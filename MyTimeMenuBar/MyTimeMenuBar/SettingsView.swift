import AppKit
import SwiftUI

struct SettingsView: View {
    @State private var draftURL: String
    var onSave: (String) -> Void
    var onCancel: () -> Void

    init(currentURL: String, onSave: @escaping (String) -> Void, onCancel: @escaping () -> Void) {
        _draftURL = State(initialValue: currentURL)
        self.onSave = onSave
        self.onCancel = onCancel
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Server URL")
            TextField("Server URL", text: $draftURL)
                .textFieldStyle(.roundedBorder)
                .frame(width: 300)
            HStack {
                Spacer()
                Button("Cancel") { onCancel() }
                    .keyboardShortcut(.cancelAction)
                Button("Save") { onSave(draftURL) }
                    .keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 360)
    }
}

/// SwiftUI's `Settings` scene / `openSettings()` reliably fails to present a
/// window for `MenuBarExtra`-only (LSUIElement) apps — a long-standing
/// platform bug. Manage the settings window directly with AppKit instead.
@MainActor
enum SettingsWindowController {
    static func show() {
        NSApp.activate(ignoringOtherApps: true)
        let currentURL = UserDefaults.standard.string(forKey: "serverBaseURL") ?? "http://bbbee.local:8000"
        var savedURL: String?

        let hosting = NSHostingController(rootView: SettingsView(
            currentURL: currentURL,
            onSave: { newURL in
                savedURL = newURL
                NSApp.stopModal()
            },
            onCancel: {
                NSApp.stopModal()
            }
        ))
        let window = NSWindow(contentViewController: hosting)
        window.title = "Settings"
        window.styleMask = [.titled, .closable]
        window.isReleasedWhenClosed = false
        // MenuBarExtra's own dropdown panel sits at an elevated window level
        // (around .statusBar) — .floating (much lower) still rendered behind
        // it. .popUpMenu is the level NSMenu's own popups use and clears it.
        window.level = .popUpMenu
        window.center()
        window.orderFrontRegardless()
        window.makeKey()

        // True app-modal: blocks interaction with the rest of the app
        // (dropdown, background sync/display loops) until Save or Cancel.
        NSApp.runModal(for: window)

        window.close()
        if let savedURL {
            UserDefaults.standard.set(savedURL, forKey: "serverBaseURL")
        }
    }
}
