import Foundation
import Observation
import UserNotifications

@MainActor
@Observable
final class TimerStore {
    var state: TodayState?
    var errorMessage: String?
    // Which entry's action produced errorMessage; nil means a general error
    // (Add form, connectivity) rather than one tied to a specific row. Lets
    // the UI show an error next to the thing that actually failed instead of
    // misattributing it to an unrelated open edit form.
    var errorEntryId: Int?
    var menuTitle: String = ""      // "1:23:45" while running, "" when idle
    var isRunning: Bool = false
    var displayNow: Date = Date()   // bumped every display tick so rows re-render

    @ObservationIgnored private var client: APIClient
    @ObservationIgnored private var loopsStarted = false
    @ObservationIgnored private var syncTask: Task<Void, Never>?
    @ObservationIgnored private var displayTask: Task<Void, Never>?
    @ObservationIgnored private var notifiedSince: String?

    init(baseURL: String) {
        client = APIClient(baseURL: baseURL)
    }

    func dismissError() {
        errorMessage = nil
        errorEntryId = nil
    }

    /// Cancels and restarts the sync loop against the new URL. Cancelling
    /// (rather than just letting the old loop keep running) also cancels any
    /// in-flight fetch against the old server — URLSession's async API
    /// observes Swift Task cancellation — so a stale response from the old
    /// server can no longer land after the new one and overwrite fresh state.
    func setBaseURL(_ url: String) {
        client.baseURL = url
        syncTask?.cancel()
        syncTask = Task { [weak self] in await self?.syncLoop() }
    }

    // MARK: Loops

    /// Start the display (1 s) and sync (~20 s) loops. Idempotent — the loops
    /// run continuously from app launch (not just while the dropdown is open),
    /// so the background sync and 4 h check keep working with the menu closed.
    func startLoops() {
        guard !loopsStarted else { return }
        loopsStarted = true
        syncTask = Task { [weak self] in await self?.syncLoop() }
        displayTask = Task { [weak self] in
            while !Task.isCancelled {
                self?.tick()
                try? await Task.sleep(for: .seconds(1))
            }
        }
    }

    private func syncLoop() async {
        while !Task.isCancelled {
            await sync(surfaceErrors: false)
            try? await Task.sleep(for: .seconds(20))
        }
    }

    /// One immediate fetch when the dropdown opens — the menubar equivalent of
    /// the web app's visibilitychange focus-refresh. User-initiated, so it
    /// surfaces new errors, but (like the background poll) never silently
    /// clears an existing one — only a manual dismiss or a new action's own
    /// success does that. Otherwise just reopening the dropdown after a
    /// failed action would wipe the banner before the user acted on it.
    func refreshOnOpen() async {
        await sync(surfaceErrors: true)
    }

    private func sync(surfaceErrors: Bool) async {
        // Self-heals the base URL from UserDefaults every cycle rather than
        // relying solely on MyTimeMenuBarApp's onChange(of: serverBaseURL) —
        // that's attached to the MenuBarExtra dropdown's content view, whose
        // show/hide lifecycle isn't guaranteed to keep observing changes made
        // in the separate Settings window while the dropdown is closed.
        if let stored = UserDefaults.standard.string(forKey: "serverBaseURL"), stored != client.baseURL {
            client.baseURL = stored
        }
        do {
            state = try await client.fetchToday()
            tick()
        } catch {
            if surfaceErrors { errorMessage = message(for: error); errorEntryId = nil }
            // Background poll failures stay silent (banner is for user actions).
        }
    }

    // MARK: Actions — every one replaces `state` wholesale from the response.

    func addEntry(projectId: Int, taskTypeId: Int, notes: String,
                  start: Bool, duration: String) async {
        await perform(entryId: nil) { try await $0.createEntry(projectId: projectId, taskTypeId: taskTypeId,
                                                 notes: notes, start: start, duration: duration) }
    }
    func startEntry(id: Int) async { await perform(entryId: id) { try await $0.start(id: id) } }
    func stopEntry(id: Int) async { await perform(entryId: id) { try await $0.stop(id: id) } }
    func setTime(id: Int, timeHM: String) async {
        await perform(entryId: id) { try await $0.setTime(id: id, timeHM: timeHM) }
    }
    func editEntry(id: Int, projectId: Int, taskTypeId: Int,
                   duration: String, notes: String) async {
        await perform(entryId: id) { try await $0.edit(id: id, projectId: projectId, taskTypeId: taskTypeId,
                                          duration: duration, notes: notes) }
    }
    func deleteEntry(id: Int) async { await perform(entryId: id) { try await $0.delete(id: id) } }

    private func perform(entryId: Int?, _ op: (APIClient) async throws -> TodayState) async {
        do {
            state = try await op(client)
            errorMessage = nil
            errorEntryId = nil
            tick()
        } catch {
            errorMessage = message(for: error)
            errorEntryId = entryId
        }
    }

    private func message(for error: Error) -> String {
        (error as? LocalizedError)?.errorDescription ?? "Something went wrong."
    }

    // MARK: Live elapsed math (recomputed, never a local counter)

    /// Elapsed seconds for an entry: base_seconds + (now - since) while running.
    func liveElapsed(_ e: Entry) -> Int {
        guard e.running, let since = e.sinceDate else { return e.baseSeconds }
        return e.baseSeconds + max(0, Int(displayNow.timeIntervalSince(since)))
    }

    func liveTotal() -> Int {
        (state?.entries ?? []).reduce(0) { $0 + liveElapsed($1) }
    }

    // MARK: Formatters

    /// Rounded HH:MM (matches the web app's fmtHms / backend fmt_hm) for rows/total.
    static func hm(_ s: Int) -> String {
        let mins = Int((Double(max(0, s)) / 60).rounded())
        return String(format: "%02d:%02d", mins / 60, mins % 60)
    }

    /// H:MM:SS (hours un-padded, seconds shown) for the ticking menubar title.
    static func hms(_ s: Int) -> String {
        let s = max(0, s)
        return "\(s / 3600):" + String(format: "%02d:%02d", (s % 3600) / 60, s % 60)
    }

    // MARK: Tick

    func tick() {
        displayNow = Date()
        guard let state else { menuTitle = ""; isRunning = false; return }
        if let running = state.entries.first(where: { $0.running }) {
            let elapsed = liveElapsed(running)
            menuTitle = Self.hms(elapsed)
            isRunning = true
            checkNotification(running, elapsed: elapsed)
        } else {
            menuTitle = ""
            isRunning = false
        }
    }

    // MARK: 4h still-running notification

    private static let notifyThresholdSeconds = 14400   // 4 hours

    /// Fire a native notification once per running-timer run (deduped on `since`)
    /// when elapsed ≥ 4 h. Because the sync loop runs even with the dropdown
    /// closed, this fires in the background too. A no-op if authorization was
    /// denied.
    private func checkNotification(_ e: Entry, elapsed: Int) {
        guard let since = e.since else { return }
        guard elapsed >= Self.notifyThresholdSeconds else { return }
        guard notifiedSince != since else { return }
        notifiedSince = since

        let content = UNMutableNotificationContent()
        content.title = "Timer still running"
        content.body = "\(e.projectName) has been running for \(Self.hoursMinutes(elapsed))"
        let request = UNNotificationRequest(identifier: UUID().uuidString,
                                            content: content, trigger: nil)
        UNUserNotificationCenter.current().add(request)
    }

    /// Compact "4h 12m" duration for the notification body.
    static func hoursMinutes(_ s: Int) -> String {
        let mins = max(0, s) / 60
        return "\(mins / 60)h \(mins % 60)m"
    }
}
