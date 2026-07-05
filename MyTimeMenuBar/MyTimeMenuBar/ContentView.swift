import SwiftUI

struct ContentView: View {
    @Bindable var store: TimerStore

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            header
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
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(entries) { e in
                        HStack {
                            Text(e.projectName)
                            Text(e.taskTypeName).foregroundStyle(.secondary)
                            Spacer()
                            Text(TimerStore.hm(store.liveElapsed(e)))
                                .monospacedDigit()
                                .foregroundStyle(e.running ? .green : .primary)
                        }
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
