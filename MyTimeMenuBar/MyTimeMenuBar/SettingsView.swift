import AppKit
import SwiftUI

struct SettingsView: View {
    @AppStorage("serverBaseURL") private var serverBaseURL = "http://bbbee.local:8000"

    var body: some View {
        Form {
            TextField("Server URL", text: $serverBaseURL)
                .textFieldStyle(.roundedBorder)
                .frame(width: 300)
        }
        .padding(20)
        .frame(width: 360, height: 90)
    }
}

/// SwiftUI's `Settings` scene / `openSettings()` reliably fails to present a
/// window for `MenuBarExtra`-only (LSUIElement) apps — a long-standing
/// platform bug. Manage the settings window directly with AppKit instead.
@MainActor
enum SettingsWindowController {
    private static var window: NSWindow?

    static func show() {
        NSApp.activate(ignoringOtherApps: true)
        if let window {
            window.orderFrontRegardless()
            window.makeKey()
            return
        }
        let hosting = NSHostingController(rootView: SettingsView())
        let newWindow = NSWindow(contentViewController: hosting)
        newWindow.title = "Settings"
        newWindow.styleMask = [.titled, .closable]
        newWindow.isReleasedWhenClosed = false
        // MenuBarExtra's own dropdown panel sits at an elevated window level
        // (around .statusBar) — .floating (much lower) still rendered behind
        // it. .popUpMenu is the level NSMenu's own popups use and clears it.
        // orderFrontRegardless() also doesn't wait on app-activation timing
        // the way makeKeyAndOrderFront(_:) can.
        newWindow.level = .popUpMenu
        newWindow.center()
        window = newWindow
        newWindow.orderFrontRegardless()
        newWindow.makeKey()
    }
}
