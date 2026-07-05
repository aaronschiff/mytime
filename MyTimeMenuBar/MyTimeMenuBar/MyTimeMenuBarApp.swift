import SwiftUI
import UserNotifications

@main
struct MyTimeMenuBarApp: App {
    @AppStorage("serverBaseURL") private var serverBaseURL = "http://bbbee.local:8000"
    @State private var store: TimerStore

    init() {
        let url = UserDefaults.standard.string(forKey: "serverBaseURL") ?? "http://bbbee.local:8000"
        let store = TimerStore(baseURL: url)
        store.startLoops()
        _store = State(initialValue: store)
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert]) { _, _ in }
    }

    var body: some Scene {
        MenuBarExtra {
            ContentView(store: store)
                .onChange(of: serverBaseURL) { _, newValue in
                    store.setBaseURL(newValue)
                }
        } label: {
            HStack(spacing: 4) {
                Image(systemName: store.menuBarSymbol)
                    .foregroundStyle(store.isRunning ? .red : .primary)
                Text(store.menuBarTimeText).monospacedDigit()
            }
        }
        .menuBarExtraStyle(.window)
    }
}
