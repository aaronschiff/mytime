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
                statusIcon
                Text(store.menuBarTimeText).monospacedDigit()
            }
        }
        .menuBarExtraStyle(.window)
    }

    /// SwiftUI's Image(systemName:) + .foregroundStyle cannot color a symbol
    /// inside a MenuBarExtra label — MenuBarExtra always renders it as a
    /// template image (forced monochrome, auto-tinted to match the menu
    /// bar), ignoring any rendering-mode or foreground-style override
    /// (confirmed via Apple Developer Forums thread 738716). Building the
    /// running-state icon as an NSImage with an explicit symbol palette
    /// color and isTemplate = false is the only way to get genuine color;
    /// the idle icon stays a plain template image so it keeps auto-adapting
    /// to the menu bar's light/dark appearance and highlight state.
    private var statusIcon: Image {
        guard store.isRunning else {
            return Image(systemName: store.menuBarSymbol)
        }
        let config = NSImage.SymbolConfiguration(paletteColors: [.systemRed])
        let nsImage = NSImage(systemSymbolName: store.menuBarSymbol, accessibilityDescription: nil)?
            .withSymbolConfiguration(config)
        nsImage?.isTemplate = false
        return Image(nsImage: nsImage ?? NSImage())
    }
}
