import SwiftUI

enum FocusTarget: Hashable {
    case container
    case addNotes
    case addDuration
    case rowTime(Int)
    case rowEditDuration(Int)
    case rowEditNotes(Int)
}

struct ContentView: View {
    @Bindable var store: TimerStore
    // At most one row edits at a time, so a Save error can be shown right
    // under the entry that caused it instead of at the bottom of the window.
    @State private var editingEntryId: Int?
    // Which row's inline elapsed-time editor (see EntryRow) is open, if any.
    // Lifted up here (rather than local per-row @State) so the background
    // tap-catcher below can close it from outside EntryRow — and, as a side
    // effect, only one row's inline time editor can ever be open at once.
    @State private var editingTimeEntryId: Int?
    // Single shared focus target for the whole dropdown (see FocusTarget):
    // every focusable field sets this back to .container when it loses
    // focus via Esc, so a second Esc always has something to land on and
    // reaches this view's own onExitCommand instead of finding no
    // responder at all (which triggers the system beep instead).
    @FocusState private var focusTarget: FocusTarget?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            header
            Divider()
            entriesList
            Divider()
            AddEntryForm(store: store, focusTarget: $focusTarget)
            // Sits right under the add form's Save/Add & start button — the
            // action most likely to produce a validation error a user needs
            // to actually read (bad duration format, etc). Suppressed only
            // when the currently-open edit form is the one the error belongs
            // to (it shows it inline instead) — an error from a different
            // row's action, or from the add form, still shows here even
            // while some other row is being edited.
            if let msg = store.errorMessage,
               !(editingEntryId != nil && editingEntryId == store.errorEntryId) {
                ErrorBanner(message: msg, onDismiss: store.errorIsConnectivity ? nil : { store.dismissError() })
            }
            Divider()
            footer
        }
        .padding(12)
        .frame(width: 340)
        .focusable()
        .focusEffectDisabled()
        .focused($focusTarget, equals: .container)
        // Closes the inline elapsed-time editor on a click anywhere outside
        // it. Buttons/TextFields/Pickers claim taps that land on them, so
        // this only ever fires for clicks that don't hit an actual control
        // (background, padding, plain text) — exactly "click outside."
        // contentShape is required: without it, the empty/text areas of
        // this VStack aren't hit-testable at all, so no tap would land here.
        .contentShape(Rectangle())
        .onTapGesture {
            editingTimeEntryId = nil
        }
        .onAppear {
            Task { await store.refreshOnOpen() }
            focusTarget = .container
        }
        .onExitCommand {
            // Esc no longer dismisses the whole dropdown: both attempts to
            // do that (NSApp.keyWindow?.close(), then NSApp.hide(nil)) left
            // the status-item icon stuck highlighted afterward, requiring an
            // extra click to reopen it — worse than not supporting
            // Esc-to-dismiss at all. No supported MenuBarExtra API was found
            // to reset that highlight (Apple Feedback FB11984872). Canceling
            // an open row edit is unaffected (it never hides the window) and
            // stays, since it's a harmless, useful Esc shortcut.
            if editingEntryId != nil {
                editingEntryId = nil
            }
        }
    }

    private var header: some View {
        HStack {
            Text("Today").font(.headline)
            Spacer()
            Text(TimerStore.hm(store.liveTotal()))
                .monospacedDigit()
                .foregroundStyle(.secondary)
        }
    }

    private var entriesList: some View {
        Group {
            if let entries = store.state?.entries, !entries.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(entries) { e in
                        EntryRow(store: store, entry: e, editingEntryId: $editingEntryId,
                                editingTimeEntryId: $editingTimeEntryId, focusTarget: $focusTarget)
                    }
                }
            } else {
                Text("No entries today").foregroundStyle(.secondary)
            }
        }
    }

    private var footer: some View {
        HStack {
            Button("Settings…") { SettingsWindowController.show() }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            Spacer()
            Button(action: openWebApp) {
                Image(systemName: "safari")
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
            Spacer()
            Button("Quit") { NSApp.terminate(nil) }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
        }
    }

    /// Opens the web app's Today page in the user's default browser, using
    /// the same server URL the menubar app itself talks to (Settings).
    private func openWebApp() {
        let base = UserDefaults.standard.string(forKey: "serverBaseURL") ?? AppDefaults.serverBaseURL
        var trimmed = base.trimmingCharacters(in: .whitespaces)
        while trimmed.hasSuffix("/") { trimmed.removeLast() }
        guard let url = URL(string: trimmed + "/today") else { return }
        NSWorkspace.shared.open(url)
    }
}

struct EntryRow: View {
    @Bindable var store: TimerStore
    let entry: Entry
    @Binding var editingEntryId: Int?
    @Binding var editingTimeEntryId: Int?
    @FocusState.Binding var focusTarget: FocusTarget?

    @State private var timeDraft = ""
    @State private var confirmingDelete = false

    private var editing: Bool { editingEntryId == entry.id }
    private var editingTime: Bool { editingTimeEntryId == entry.id }
    private var canEditTime: Bool { !entry.running && !entry.locked }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            row
            if editing {
                EntryEditForm(store: store, entry: entry, focusTarget: $focusTarget) { editingEntryId = nil }
            }
        }
        // If this entry becomes locked (e.g. invoiced from another client)
        // while its edit form is open, force it closed rather than let Save
        // submit against a since-changed entry.
        .onChange(of: entry.locked) { _, locked in
            if locked {
                if editing { editingEntryId = nil }
                confirmingDelete = false
            }
        }
        // Same idea for the inline time editor: if the entry starts running
        // or becomes locked elsewhere while it's open, close it rather than
        // let a stale edit submit against the new state.
        .onChange(of: canEditTime) { _, canEdit in
            if !canEdit, editingTime { editingTimeEntryId = nil }
        }
        // Belt-and-suspenders alongside ContentView's tap-outside catcher:
        // covers focus moving off this field for reasons that aren't a
        // plain click (e.g. Tab to another field).
        .onChange(of: focusTarget) { _, newValue in
            if editingTime, newValue != .rowTime(entry.id) {
                editingTimeEntryId = nil
            }
        }
        // If this entry is deleted while its edit form is open, ForEach
        // removes this view — reset editingEntryId/editingTimeEntryId so a
        // dangling reference doesn't permanently suppress the bottom error
        // banner, or keep a since-removed row's editor "open" forever.
        .onDisappear {
            if editing { editingEntryId = nil }
            if editingTime { editingTimeEntryId = nil }
        }
    }

    private var row: some View {
        HStack(spacing: 8) {
            HStack(spacing: 4) {
                // Clear circle (not just omitted) when stopped, so the name
                // doesn't shift over when the dot appears/disappears on
                // start/stop.
                if entry.running {
                    Circle().fill(.green).frame(width: 6, height: 6)
                } else {
                    Color.clear.frame(width: 6, height: 6)
                }
                VStack(alignment: .leading, spacing: 1) {
                    Text(entry.projectName)
                    Text(entry.taskTypeName).font(.caption).foregroundStyle(.secondary)
                }
            }

            Spacer()

            // Start/stop toggle, right next to the elapsed time it controls
            // (hidden for locked entries; a lock icon stands in so it's
            // clear why there are no controls).
            if entry.locked {
                Image(systemName: "lock.fill").foregroundStyle(.secondary)
            } else {
                Button {
                    Task {
                        if entry.running { await store.stopEntry(id: entry.id) }
                        else { await store.startEntry(id: entry.id) }
                    }
                } label: {
                    Image(systemName: entry.running ? "stop.fill" : "play.fill")
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }

            // Click-to-edit elapsed (stopped, unlocked only).
            if editingTime {
                TextField("HH:MM", text: $timeDraft)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 60)
                    .monospacedDigit()
                    .focused($focusTarget, equals: .rowTime(entry.id))
                    .onExitCommand {
                        focusTarget = .container
                        editingTimeEntryId = nil
                    }
                    .onSubmit {
                        Task { await store.setTime(id: entry.id, timeHM: timeDraft) }
                        editingTimeEntryId = nil
                    }
            } else {
                let label = Text(TimerStore.hm(store.liveElapsed(entry)))
                    .monospacedDigit()
                    .foregroundStyle(entry.running ? .green : .primary)
                if canEditTime {
                    Button {
                        timeDraft = TimerStore.hm(store.liveElapsed(entry))
                        editingTimeEntryId = entry.id
                        focusTarget = .rowTime(entry.id)
                    } label: { label }
                    .buttonStyle(.plain)
                } else {
                    label
                }
            }

            // Full edit (hidden for locked entries).
            if !entry.locked {
                Button {
                    editingEntryId = editing ? nil : entry.id
                } label: {
                    Image(systemName: "pencil")
                        .frame(width: 20, height: 20)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }

            // Delete (hidden for locked entries). A system confirmationDialog
            // conflicts with MenuBarExtra's special window (same class of bug
            // as openSettings — see SettingsWindowController) and can leave
            // the dropdown in a stuck, invisible state. Confirm inline instead.
            if !entry.locked {
                if confirmingDelete {
                    Text("Delete?").font(.caption).foregroundStyle(.secondary)
                    Button {
                        confirmingDelete = false
                        Task { await store.deleteEntry(id: entry.id) }
                    } label: {
                        Image(systemName: "checkmark.circle.fill")
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.red)
                    Button {
                        confirmingDelete = false
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)
                } else {
                    Button {
                        confirmingDelete = true
                    } label: {
                        Image(systemName: "trash")
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)
                }
            }
        }
        .opacity(entry.locked ? 0.55 : 1.0)
    }
}

struct AddEntryForm: View {
    @Bindable var store: TimerStore
    @FocusState.Binding var focusTarget: FocusTarget?

    @State private var projectId: Int?
    @State private var taskTypeId: Int?
    @State private var notes = ""
    @State private var duration = ""

    private var projects: [ProjectRef] { store.state?.projects ?? [] }
    private var taskTypes: [TaskTypeRef] { store.state?.taskTypes ?? [] }
    private var canSubmit: Bool { projectId != nil && taskTypeId != nil }

    /// Mirrors the web app's toggling behavior: an empty/zero duration means
    /// "Add & start" a running entry; a non-zero duration means "Save" a
    /// stopped entry with that elapsed time. Never both at once.
    private var isDurationZero: Bool {
        let v = duration.trimmingCharacters(in: .whitespaces)
        return v.isEmpty || v == "00:00" || v == "0:00"
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("New entry").font(.caption).foregroundStyle(.secondary)

            Picker("Project", selection: $projectId) {
                Text("Project…").tag(Int?.none)
                ForEach(projects) { p in Text(p.name).tag(Int?.some(p.id)) }
            }
            Picker("Task type", selection: $taskTypeId) {
                Text("Task type…").tag(Int?.none)
                ForEach(taskTypes) { t in Text(t.name).tag(Int?.some(t.id)) }
            }

            TextField("Notes (optional)", text: $notes)
                .textFieldStyle(.roundedBorder)
                .focused($focusTarget, equals: .addNotes)
                .onExitCommand { focusTarget = .container }

            HStack {
                TextField("HH:MM", text: $duration)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 70)
                    .focused($focusTarget, equals: .addDuration)
                    .onExitCommand { focusTarget = .container }
                Spacer()
                Button(isDurationZero ? "Add & start" : "Save") {
                    submit(start: isDurationZero)
                }
                .disabled(!canSubmit)
                .keyboardShortcut(.defaultAction)
            }
        }
    }

    private func submit(start: Bool) {
        guard let projectId, let taskTypeId else { return }
        let dur = duration.isEmpty ? "00:00" : duration
        Task {
            await store.addEntry(projectId: projectId, taskTypeId: taskTypeId,
                                 notes: notes, start: start, duration: dur)
            // On success, reset the form. On error the banner shows and state is unchanged.
            if store.errorMessage == nil {
                notes = ""; duration = ""; self.projectId = nil; self.taskTypeId = nil
            }
        }
    }
}
struct ErrorBanner: View {
    let message: String
    // nil hides the dismiss button entirely — used for connectivity errors,
    // which auto-clear on their own once the server is reachable again and
    // shouldn't be dismissable in the meantime (see TimerStore.errorIsConnectivity).
    var onDismiss: (() -> Void)?

    var body: some View {
        HStack(alignment: .top, spacing: 6) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
            Text(message)
                .font(.callout)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)
            if let onDismiss {
                Button(action: onDismiss) {
                    Image(systemName: "xmark.circle.fill")
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }
        }
        .padding(8)
        .background(.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 6))
    }
}

struct EntryEditForm: View {
    @Bindable var store: TimerStore
    let entry: Entry
    @FocusState.Binding var focusTarget: FocusTarget?
    var onDone: () -> Void

    @State private var projectId: Int
    @State private var taskTypeId: Int
    @State private var duration: String
    @State private var notes: String
    // What the duration field was prefilled with. If it's still this exact
    // value at Save, the duration is omitted from the request entirely so the
    // backend leaves the entry's time (and any live run) untouched — the
    // prefill is a minute-rounded snapshot taken when the form opened, and
    // writing it back would discard time accrued since then.
    private let durationPrefill: String

    init(store: TimerStore, entry: Entry, focusTarget: FocusState<FocusTarget?>.Binding, onDone: @escaping () -> Void) {
        self.store = store
        self.entry = entry
        self._focusTarget = focusTarget
        self.onDone = onDone
        _projectId = State(initialValue: entry.projectId)
        _taskTypeId = State(initialValue: entry.taskTypeId)
        let prefill = TimerStore.hm(store.liveElapsed(entry))
        durationPrefill = prefill
        _duration = State(initialValue: prefill)
        _notes = State(initialValue: entry.notes)
    }

    private var projects: [ProjectRef] { store.state?.projects ?? [] }
    private var taskTypes: [TaskTypeRef] { store.state?.taskTypes ?? [] }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Picker("Project", selection: $projectId) {
                ForEach(projects) { p in Text(p.name).tag(p.id) }
            }
            Picker("Task type", selection: $taskTypeId) {
                ForEach(taskTypes) { t in Text(t.name).tag(t.id) }
            }
            HStack {
                Text("Time").foregroundStyle(.secondary)
                TextField("HH:MM", text: $duration)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 70)
                    .monospacedDigit()
                    .focused($focusTarget, equals: .rowEditDuration(entry.id))
                    .onExitCommand { focusTarget = .container }
            }
            TextField("Notes", text: $notes)
                .textFieldStyle(.roundedBorder)
                .focused($focusTarget, equals: .rowEditNotes(entry.id))
                .onExitCommand { focusTarget = .container }
            if let msg = store.errorMessage, store.errorEntryId == entry.id {
                ErrorBanner(message: msg, onDismiss: store.errorIsConnectivity ? nil : { store.dismissError() })
            }
            HStack {
                Spacer()
                Button("Cancel") {
                    if store.errorEntryId == entry.id { store.dismissError() }
                    onDone()
                }
                Button("Save") {
                    Task {
                        let trimmed = duration.trimmingCharacters(in: .whitespaces)
                        await store.editEntry(id: entry.id, projectId: projectId,
                                              taskTypeId: taskTypeId,
                                              duration: trimmed == durationPrefill ? nil : trimmed,
                                              notes: notes)
                        if store.errorMessage == nil { onDone() }
                    }
                }
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(8)
        .background(.gray.opacity(0.08), in: RoundedRectangle(cornerRadius: 6))
    }
}
