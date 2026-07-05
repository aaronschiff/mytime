import SwiftUI

struct ContentView: View {
    @Bindable var store: TimerStore
    // At most one row edits at a time, so a Save error can be shown right
    // under the entry that caused it instead of at the bottom of the window.
    @State private var editingEntryId: Int?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            header
            Divider()
            entriesList
            Divider()
            AddEntryForm(store: store)
            // Sits right under the add form's Save/Add & start button — the
            // action most likely to produce a validation error a user needs
            // to actually read (bad duration format, etc). Suppressed only
            // when the currently-open edit form is the one the error belongs
            // to (it shows it inline instead) — an error from a different
            // row's action, or from the add form, still shows here even
            // while some other row is being edited.
            if let msg = store.errorMessage,
               !(editingEntryId != nil && editingEntryId == store.errorEntryId) {
                ErrorBanner(message: msg) { store.dismissError() }
            }
            Divider()
            footer
        }
        .padding(12)
        .frame(width: 340)
        .onAppear { Task { await store.refreshOnOpen() } }
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
                        EntryRow(store: store, entry: e, editingEntryId: $editingEntryId)
                    }
                }
            } else {
                Text("No entries today").foregroundStyle(.secondary)
            }
        }
    }

    private var footer: some View {
        HStack {
            Spacer()
            Button("Settings…") { SettingsWindowController.show() }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            Button("Quit") { NSApp.terminate(nil) }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
        }
    }
}

struct EntryRow: View {
    @Bindable var store: TimerStore
    let entry: Entry
    @Binding var editingEntryId: Int?

    @State private var editingTime = false
    @State private var timeDraft = ""
    @State private var confirmingDelete = false

    private var editing: Bool { editingEntryId == entry.id }
    private var canEditTime: Bool { !entry.running && !entry.locked }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            row
            if editing {
                EntryEditForm(store: store, entry: entry) { editingEntryId = nil }
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
            if !canEdit { editingTime = false }
        }
        // If this entry is deleted while its edit form is open, ForEach
        // removes this view — reset editingEntryId so a dangling reference
        // doesn't permanently suppress the bottom error banner for the rest
        // of the session (its suppression check compares against this id).
        .onDisappear {
            if editing { editingEntryId = nil }
        }
    }

    private var row: some View {
        HStack(spacing: 8) {
            // Start/stop toggle (hidden for locked entries; a lock icon
            // stands in so it's clear why there are no controls).
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
                .foregroundStyle(entry.running ? .red : .green)
            }

            VStack(alignment: .leading, spacing: 1) {
                Text(entry.projectName)
                Text(entry.taskTypeName).font(.caption).foregroundStyle(.secondary)
            }

            Spacer()

            // Click-to-edit elapsed (stopped, unlocked only).
            if editingTime {
                TextField("HH:MM", text: $timeDraft)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 60)
                    .monospacedDigit()
                    .onSubmit {
                        Task { await store.setTime(id: entry.id, timeHM: timeDraft) }
                        editingTime = false
                    }
            } else {
                let label = Text(TimerStore.hm(store.liveElapsed(entry)))
                    .monospacedDigit()
                    .foregroundStyle(entry.running ? .green : .primary)
                if canEditTime {
                    Button {
                        timeDraft = TimerStore.hm(store.liveElapsed(entry))
                        editingTime = true
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

            HStack {
                TextField("HH:MM", text: $duration)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 70)
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
    var onDismiss: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 6) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
            Text(message)
                .font(.callout)
                .fixedSize(horizontal: false, vertical: true)
                .frame(maxWidth: .infinity, alignment: .leading)
            Button(action: onDismiss) {
                Image(systemName: "xmark.circle.fill")
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
        }
        .padding(8)
        .background(.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 6))
    }
}

struct EntryEditForm: View {
    @Bindable var store: TimerStore
    let entry: Entry
    var onDone: () -> Void

    @State private var projectId: Int
    @State private var taskTypeId: Int
    @State private var duration: String
    @State private var notes: String

    init(store: TimerStore, entry: Entry, onDone: @escaping () -> Void) {
        self.store = store
        self.entry = entry
        self.onDone = onDone
        _projectId = State(initialValue: entry.projectId)
        _taskTypeId = State(initialValue: entry.taskTypeId)
        // Live elapsed, not entry.baseSeconds — the backend stops a running
        // entry and overwrites its total from this value unconditionally, so
        // prefilling from the stale stored base would silently discard all
        // the time it accumulated while running.
        _duration = State(initialValue: TimerStore.hm(store.liveElapsed(entry)))
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
            }
            TextField("Notes", text: $notes)
                .textFieldStyle(.roundedBorder)
            if let msg = store.errorMessage, store.errorEntryId == entry.id {
                ErrorBanner(message: msg) { store.dismissError() }
            }
            HStack {
                Spacer()
                Button("Cancel") {
                    if store.errorEntryId == entry.id { store.dismissError() }
                    onDone()
                }
                Button("Save") {
                    Task {
                        await store.editEntry(id: entry.id, projectId: projectId,
                                              taskTypeId: taskTypeId,
                                              duration: duration, notes: notes)
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

