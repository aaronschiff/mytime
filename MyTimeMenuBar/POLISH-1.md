# Polish for MyTimeMenuBar

[x] Make Settings a proper modal dialog box with Save and Cancel buttons — Save/Cancel implemented; ~~true app-modal (NSApp.runModal)~~ reverted to non-modal after true app-modal was found to hide the whole dropdown for its duration with no supported way to bring it back (see docs/superpowers/specs/2026-07-06-menubar-polish-1-design.md)
[x] Move "Settings ..." to the bottom left corner of the app window, keep Quit at the bottom right
[x] Add a button to the bottom middle of the app window to launch the web app version of Mytime in the user's default browser (using the URL from Settings)
[ ] ~~Pressing Esc key while the MytimeMenubar app window is displayed dismisses it~~ — reverted: dismissing the dropdown via Esc left the menubar icon stuck highlighted, requiring an extra click to reopen it (worse than no Esc-dismiss at all); no supported MenuBarExtra API found to reset that highlight (Apple Feedback FB11984872). Esc still cancels an open row edit form, and still defocuses a text field without closing anything.
[x] Change the menubar icon as follows: 
	- Remove seconds from the running timer in the menubar, just show H:MM (1 digit for hours unless 2 digits required)
	- When stopped, icon shows a non-coloured "play" icon (right-pointing triangle) plus tracked time for today's most recent running timer (0:00 if no time tracked yet) — shows the *running entry's own* elapsed time while running, per a design revision agreed with the user (see docs/superpowers/specs/2026-07-06-menubar-polish-1-design.md)
	- ~~When running, icon shows a red "stop" icon (like running timers) plus today's total tracked time~~ — revised: shows the running entry's own elapsed time, not the daily total (see spec)
	- ~~Clicking the "play" icon restarts the most recent running timer without showing the app window, if there was a recent running timer, otherwise shows the app window~~ — descoped: whole label is a single click target that opens the window (see spec, "Click behavior")
	- ~~Clicking the "stop" icon stops the running timer without showing the app window~~ — descoped, same reason
	- Clicking on the time digits shows the app window and does not start or stop any timer

