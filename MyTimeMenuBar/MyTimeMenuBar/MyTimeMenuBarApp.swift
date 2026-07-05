import SwiftUI
import UserNotifications

@main
struct MyTimeMenuBarApp: App {
    @AppStorage("serverBaseURL") private var serverBaseURL = AppDefaults.serverBaseURL
    @State private var store: TimerStore

    init() {
        let url = UserDefaults.standard.string(forKey: "serverBaseURL") ?? AppDefaults.serverBaseURL
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
                    .renderingMode(.original)
                    .foregroundStyle(store.isRunning ? .red : .primary)
                Text(store.menuBarTimeText).monospacedDigit()
            }
        }
        .menuBarExtraStyle(.window)
    }
}
