# Mytime user testing

## Bugs

[x] Added and started a new timer, it started at 12:00, not 00:00. When stopped it showed the correct amount of time. 
[x] Overview bar charts don't distinguish any over-budget amount. Add a vertical line representing the budget on the bar.
[x] I was able to enter the Edit time entry screen of an invoiced time entry from the Today page, which caused an Internal Server Error when I pressed save.
[x] Editing a time entry to change the project didn't stick when saved.

## Backlog

Refer to `BACKLOG.md` and handle: 

[x] Code cleanup: do all items in the backlog
[x] Keyboard shortcuts: Just start/stop timer and quick-add time entry
[x] Browser notifications: Add a notification for a potentially forgotten timer if it has been running for more than 4 hours since its most recent start
    - Notification based on time since most recent start, not total time of the timer
    - So for example if a timer that had 3 hours on it was stopped and then restarted later and left running continuously, the notification wouldn't trigger until the timer showed 7 hours in total (i.e. 4 hours since the restart)
[x] Data backups:
    - Create an automated daily database backup task
    - Copy database to `/data/mytime-backup/` (`/data/` is a separate physical drive on `bbbee.local`)
    - Retain individual daily database snapshots for the past 28 days
    - For earlier backups (before the past 28 days), retain one snapshot every 28 days

## Clients

[x] Make clients their own first-class entity in the database
[x] At present, the only client attribute is client name, but more attributes may be added in future
[x] Add a "Clients" page, put it after "Time" in the top menu
[x] Clients page shows a list of clients with ability to view / edit / delete
[x] Clients that have projects with any tracked time cannot be deleted
[x] Viewing a client shows the same list as the Projects page, but only for that client's projects

## UI polish

### Edit buttons

[x] Make all Edit buttons a button (like Delete), not a hyperlink

### Save/cancel behaviour

[x] All Save and Cancel buttons in forms should return to the previous view where the form was invoked from

### Date and number formatting

[x] Format all displayed dates as DD-MM-YYYY
[x] Format all times as hh:mm rounded to the nearest minute
[x] Format all dollar amounts rounded to the nearest dollar with currency symbol prefixed

### New project form

[x] Client name autocomplete based on clients from past projects
[x] Hourly rate and budget prefix currency symbol
[x] Remove up/down arrow clickers from hourly rate and budget fields
[x] Make client name, project name, description fields wider
[x] Make description field 4 lines high to start with, check font size is same as other fields

### Today page

[x] Make the time of stopped timers directly editable by clicking on the time recorded. Keep the edit button and separate edit form in case other things need to be edited
[x] Stop the green dot from pulsing on an active timer (just a solid dot is fine)
[x] Remove Start / Edit / Delete buttons for invoiced time entries and show "Invoiced"
[x] Have two modalities for adding a new time entry: 
    - "Add and start": As currently implemented with a new timer that auto-starts from zero
    - "Save": The user enters a time entry and this is saved but the timer is not started
    - Distinguish between these two modalities by whether the user has edited the timer's time from 00:00 to a positive amount of time
    - Actively change the button from "Add and start" to "Save" if the user edits the timer's time

### New time entry

[x] Ask for confirmation if the selected date is in the future

### Edit time entry

[x] Hours input box is too wide
[x] Make time a single hh:mm text field, directly editable
[x] Get rid of up/down arrow clickers on hours and minutes
[x] Make notes field wider

### Edit project form

[x] Hourly rate and budget prefix currency symbol
[x] Make description field wider and 4 lines high to start with

### Overview page

[x] Match colours of invoiced / uninvoiced / remaining labels under bar charts to bar colours
[x] Make any over budget amounts red
[x] Add a "New invoice" button to the card for each project
[x] Bar chart needs a small top margin

### New invoice page

[x] In each row of the task time summary, add the dollar amount (based on invoiced time)
[x] Make invoiced time a single hh:mm text field, directly editable, remove the up/down arrow clickers
[x] Add a total row showing totals for tracked time, invoiced time, invoiced dollars
[x] Round all dollar amounts, don't show cents
[x] Display total amount invoiced so far and budget remaining 
[x] Invoice number should be editable (so I can match my invoicing system) and check these are unique among known prior invoices 

### Project page

[x] Make it visually obvious when "Active" or "Archived" is selected

### Invoice list view

[x] Add "invoices" to the top menu just before "Settings", which opens a list page of all invoices in reverse chronological order
