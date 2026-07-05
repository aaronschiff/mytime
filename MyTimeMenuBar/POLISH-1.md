# Polish for MyTimeMenuBar

[x] Make Settings a proper modal dialog box with Save and Cancel buttons
[ ] Move "Settings ..." to the bottom left corner of the app window, keep Quit at the bottom right
[ ] Add a button to the bottom middle of the app window to launch the web app version of Mytime in the user's default browser (using the URL from Settings)
[ ] Pressing Esc key while the MytimeMenubar app window is displayed dismisses it
[ ] Change the menubar icon as follows: 
	- Remove seconds from the running timer in the menubar, just show H:MM (1 digit for hours unless 2 digits required)
	- When stopped, icon shows a non-coloured "play" icon (right-pointing triangle) plus tracked time for today's most recent running timer (0:00 if no time tracked yet)
	- When running, icon shows a red "stop" icon (like running timers) plus today's total tracked time
	- Clicking the "play" icon restarts the most recent running timer without showing the app window, if there was a recent running timer, otherwise shows the app window
	- Clicking the "stop" icon stops the running timer without showing the app window
	- Clicking on the time digits shows the app window and does not start or stop any timer

