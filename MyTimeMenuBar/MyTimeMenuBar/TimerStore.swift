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
    // True when errorMessage is a "can't reach the server" failure rather
    // than a validation/HTTP error. Connectivity errors aren't user-
    // dismissable (dismissError() below is a no-op for them) and clear
    // themselves the moment any request succeeds again — see sync()/perform().
    var errorIsConnectivity: Bool = false
    var menuBarSymbol: String = "stop.fill"  // menubar icon: "stop.fill" idle (uncolored), "circle.fill" running (green dot)
    var menuBarTimeText: String = "0:00"     // "H:MM" shown next to the menubar icon
    var isRunning: Bool = false
    var displayNow: Date = Date()   // bumped every display tick so rows re-render

    @ObservationIgnored private var client: APIClient
    @ObservationIgnored private var loopsStarted = false
    @ObservationIgnored private var syncTask: Task<Void, Never>?
    @ObservationIgnored private var displayTask: Task<Void, Never>?
    @ObservationIgnored private var notifiedSince: String?

    /// Id of the most recently *running* entry, persisted directly via
    /// UserDefaults (not @AppStorage — TimerStore is a plain @Observable
    /// class, not a View) so it survives app relaunches. 0 means "never
    /// tracked one" (valid entry ids from the backend are >= 1). Updated in
    /// `tick()` whenever an entry is running; left untouched when nothing is
    /// running, so the menubar can still show "what I'd resume" after a stop.
    private var lastRunningEntryId: Int? {
        get {
            let v = UserDefaults.standard.integer(forKey: "lastRunningEntryId")
            return v == 0 ? nil : v
        }
        set {
            guard let newValue else { return }
            UserDefaults.standard.set(newValue, forKey: "lastRunningEntryId")
        }
    }

    init(baseURL: String) {
        client = APIClient(baseURL: baseURL)
    }

    /// No-op for connectivity errors — those clear themselves once the
    /// server is reachable again, and shouldn't be dismissable in the
    /// meantime (see errorIsConnectivity).
    func dismissError() {
        guard !errorIsConnectivity else { return }
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
            // Auto-heal: a visible connectivity error clears itself the
            // moment any fetch succeeds again, even one from the silent
            // background loop — that's the whole point of not making the
            // user dismiss it manually.
            if errorIsConnectivity {
                errorMessage = nil
                errorEntryId = nil
                errorIsConnectivity = false
            }
        } catch {
            let connectivity = isConnectivityError(error)
            // Connectivity errors always surface, even from the silent
            // background loop — that's what makes the banner track live
            // reachability (e.g. right after the user points Settings at a
            // dead address) instead of only appearing after some unrelated
            // user action. Other background-poll failures (a malformed
            // response, say) still stay silent — the banner is for user
            // actions in that case.
            if surfaceErrors || connectivity {
                errorMessage = message(for: error)
                errorEntryId = nil
                errorIsConnectivity = connectivity
            }
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
                   duration: String?, notes: String) async {
        await perform(entryId: id) { try await $0.edit(id: id, projectId: projectId, taskTypeId: taskTypeId,
                                          duration: duration, notes: notes) }
    }
    func deleteEntry(id: Int) async { await perform(entryId: id) { try await $0.delete(id: id) } }

    private func perform(entryId: Int?, _ op: (APIClient) async throws -> TodayState) async {
        do {
            state = try await op(client)
            errorMessage = nil
            errorEntryId = nil
            errorIsConnectivity = false
            tick()
        } catch {
            errorMessage = message(for: error)
            errorEntryId = entryId
            errorIsConnectivity = isConnectivityError(error)
        }
    }

    private func message(for error: Error) -> String {
        (error as? LocalizedError)?.errorDescription ?? "Something went wrong."
    }

    private func isConnectivityError(_ error: Error) -> Bool {
        if case APIError.connectivity = error { return true }
        return false
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

    /// H:MM (hours un-padded, minutes zero-padded) for the menubar icon's
    /// time text — same rounding as `hm`, just without the leading zero.
    static func hmUnpadded(_ s: Int) -> String {
        let mins = Int((Double(max(0, s)) / 60).rounded())
        return "\(mins / 60):" + String(format: "%02d", mins % 60)
    }

    // MARK: Tick

    func tick() {
        displayNow = Date()
        guard let state else {
            isRunning = false
            menuBarSymbol = "stop.fill"
            menuBarTimeText = "0:00"
            return
        }
        if let running = state.entries.first(where: { $0.running }) {
            isRunning = true
            lastRunningEntryId = running.id
            let elapsed = liveElapsed(running)
            menuBarSymbol = "circle.fill"
            menuBarTimeText = Self.hmUnpadded(elapsed)
            checkNotification(running, elapsed: elapsed)
        } else {
            isRunning = false
            menuBarSymbol = "stop.fill"
            if let id = lastRunningEntryId, let entry = state.entries.first(where: { $0.id == id }) {
                menuBarTimeText = Self.hmUnpadded(liveElapsed(entry))
            } else {
                menuBarTimeText = "0:00"
            }
        }
    }

    // MARK: 4h still-running notification

    private static let notifyThresholdSeconds = 14400   // 4 hours

    /// Fire a native notification once per running-timer run (deduped on `since`)
    /// when the *current continuous run* — time since this `since`, not the
    /// entry's cumulative total across earlier stop/restart cycles — reaches
    /// 4 h. Matches the web app's reference behavior (timer-tick.js's
    /// `_checkNotification`, which only ever looks at `now - since`). Because
    /// the sync loop runs even with the dropdown closed, this fires in the
    /// background too. A no-op if authorization was denied.
    private func checkNotification(_ e: Entry, elapsed: Int) {
        guard let since = e.since else { return }
        let continuousElapsed = elapsed - e.baseSeconds
        guard continuousElapsed >= Self.notifyThresholdSeconds else { return }
        guard notifiedSince != since else { return }
        notifiedSince = since

        let content = UNMutableNotificationContent()
        content.title = "Timer still running"
        content.body = "\(e.projectName) has been running for \(Self.hoursMinutes(continuousElapsed))"
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
