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
            HStack(spacing: 8) {
                statusIcon
                Text(store.menuBarTimeText).monospacedDigit().offset(y: 2)
            }
        }
        .menuBarExtraStyle(.window)
    }

    /// Menu bar text renders at the system menu font's default point size
    /// (13pt); the status icons are sized relative to that so "N% smaller"
    /// tweaks have a stable baseline to shrink from.
    private static let baseIconPointSize: CGFloat = 13
    /// Running dot (circle.fill): 30% smaller than the text baseline.
    private static let runningIconPointSize = baseIconPointSize * 0.7
    /// Idle square (stop.fill): 10% smaller than the text baseline.
    private static let idleIconPointSize = baseIconPointSize * 0.9

    /// SwiftUI's Image(systemName:) + .foregroundStyle cannot color a symbol
    /// inside a MenuBarExtra label — MenuBarExtra always renders it as a
    /// template image (forced monochrome, auto-tinted to match the menu
    /// bar), ignoring any rendering-mode or foreground-style override
    /// (confirmed via Apple Developer Forums thread 738716). Building the
    /// running-state icon (a green dot) as an NSImage with an explicit
    /// symbol palette color and isTemplate = false is the only way to get
    /// genuine color; the idle icon (a stop square) stays a plain template
    /// image so it keeps auto-adapting to the menu bar's light/dark
    /// appearance and highlight state.
    private var statusIcon: some View {
        let image: Image
        if store.isRunning {
            let sizeConfig = NSImage.SymbolConfiguration(pointSize: Self.runningIconPointSize, weight: .regular)
            let colorConfig = NSImage.SymbolConfiguration(paletteColors: [.systemGreen])
            let config = sizeConfig.applying(colorConfig)
            let nsImage = NSImage(systemSymbolName: store.menuBarSymbol, accessibilityDescription: nil)?
                .withSymbolConfiguration(config)
            nsImage?.isTemplate = false
            image = Image(nsImage: nsImage ?? NSImage())
        } else {
            image = Image(systemName: store.menuBarSymbol)
        }
        // The .font() modifier only affects the plain-systemName idle image;
        // the running image already has its size baked in via
        // SymbolConfiguration(pointSize:) above, so this call is a no-op for
        // it — applied unconditionally just to keep both branches the same
        // concrete `some View` return type.
        return image.font(.system(size: store.isRunning ? Self.runningIconPointSize : Self.idleIconPointSize))
    }
}
