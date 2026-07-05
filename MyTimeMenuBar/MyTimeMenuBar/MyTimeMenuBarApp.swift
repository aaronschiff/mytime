import SwiftUI

@main
struct MyTimeMenuBarApp: App {
    @AppStorage("serverBaseURL") private var serverBaseURL = "http://bbbee.local:8000"
    @State private var store: TimerStore

    init() {
        let url = UserDefaults.standard.string(forKey: "serverBaseURL") ?? "http://bbbee.local:8000"
        let store = TimerStore(baseURL: url)
        store.startLoops()
        _store = State(initialValue: store)
    }

    var body: some Scene {
        MenuBarExtra {
            ContentView(store: store)
                .onChange(of: serverBaseURL) { _, newValue in
                    store.setBaseURL(newValue)
                }
        } label: {
            if store.isRunning {
                Text(store.menuTitle).monospacedDigit()
            } else {
                Image(systemName: "clock")
            }
        }
        .menuBarExtraStyle(.window)
    }
}
