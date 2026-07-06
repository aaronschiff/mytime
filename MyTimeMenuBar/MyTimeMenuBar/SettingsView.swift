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
///
/// Non-modal by design: an earlier true-app-modal version (NSApp.runModal)
/// made the MenuBarExtra dropdown itself disappear for the duration and not
/// reappear afterward (no supported SwiftUI API to reopen it) — an OS-level
/// side effect of going app-modal, not something fixable at this layer. This
/// version keeps Save/Cancel (no more live-saving on every keystroke) but
/// shows the window alongside the still-open dropdown, exactly as before.
@MainActor
enum SettingsWindowController {
    static func show() {
        NSApp.activate(ignoringOtherApps: true)
        let currentURL = UserDefaults.standard.string(forKey: "serverBaseURL") ?? AppDefaults.serverBaseURL

        var window: NSWindow!
        let hosting = NSHostingController(rootView: SettingsView(
            currentURL: currentURL,
            onSave: { newURL in
                UserDefaults.standard.set(newURL, forKey: "serverBaseURL")
                window.close()
            },
            onCancel: {
                window.close()
            }
        ))
        window = NSWindow(contentViewController: hosting)
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
    }
}
