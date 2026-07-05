# Polish for MyTimeMenuBar

[x] Make Settings a proper modal dialog box with Save and Cancel buttons
[x] Move "Settings ..." to the bottom left corner of the app window, keep Quit at the bottom right
[x] Add a button to the bottom middle of the app window to launch the web app version of Mytime in the user's default browser (using the URL from Settings)
[x] Pressing Esc key while the MytimeMenubar app window is displayed dismisses it
[x] Change the menubar icon as follows: 
	- Remove seconds from the running timer in the menubar, just show H:MM (1 digit for hours unless 2 digits required)
	- When stopped, icon shows a non-coloured "play" icon (right-pointing triangle) plus tracked time for today's most recent running timer (0:00 if no time tracked yet) — shows the *running entry's own* elapsed time while running, per a design revision agreed with the user (see docs/superpowers/specs/2026-07-06-menubar-polish-1-design.md)
	- ~~When running, icon shows a red "stop" icon (like running timers) plus today's total tracked time~~ — revised: shows the running entry's own elapsed time, not the daily total (see spec)
	- ~~Clicking the "play" icon restarts the most recent running timer without showing the app window, if there was a recent running timer, otherwise shows the app window~~ — descoped: whole label is a single click target that opens the window (see spec, "Click behavior")
	- ~~Clicking the "stop" icon stops the running timer without showing the app window~~ — descoped, same reason
	- Clicking on the time digits shows the app window and does not start or stop any timer

