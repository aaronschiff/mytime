import SwiftUI

struct ContentView: View {
    @Bindable var store: TimerStore

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            header
            if let msg = store.errorMessage {
                HStack(alignment: .top, spacing: 6) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(.orange)
                    Text(msg)
                        .font(.callout)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading)
                    Button {
                        store.errorMessage = nil
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)
                }
                .padding(8)
                .background(.orange.opacity(0.12), in: RoundedRectangle(cornerRadius: 6))
            }
            Divider()
            entriesList
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
                        EntryRow(store: store, entry: e)
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

    @State private var editingTime = false
    @State private var timeDraft = ""
    @State private var confirmingDelete = false

    private var canEditTime: Bool { !entry.running && !entry.locked }

    var body: some View {
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
                TextField("H:MM", text: $timeDraft)
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
