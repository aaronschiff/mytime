# Mytime user testing round 3

## Bugs

[x] Starting a timer that is at an exact number of hours (e.g. 02:00) makes it momentarily display one minute less (e.g. 01:59) on the Today view
[x] Archived projects should not be editable
    - Don't show the "Edit project" button on the project view of an archived project
[x] Time entries should not be able to be added to archived projects
    - Don't show the "New time entry" button on the project view of an archived project
[x] Combinations of client x project name should be required to be unique (should not be able to create duplicate projects for a client)

## UI polish

### General

[x] Make all buttons visually consistent in terms of height and corner radius
[x] Make all input fields have a little top margin so they don't touch their labels above
[x] Buttons should be the same height as dropdown lists
[x] Manually created or edited time entries greater than or equal to 10 hours should request confirmation from the user as these are likely to be errors
[x] Truncate time entry notes in all list views if they are > 3 words

### New invoice view

[x] Incorporate the GST and total incl GST values as rows in the task summary table
[x] Dollar values **in this view** should include cents

### Existing invoice view

[x] Right-align values in the Amount column
[x] Dollar values **in this view** should include cents

### Today view

[x] Remove client names from timer list
[x] Add a reminder of the keyboard shortcuts at the top

### Projects view

[x] Right-align values in budget, invoiced, uninvoiced columns
[x] Add date started column
[x] Sort projects reverse chronological by date started

### Individual project view

[x] Invoice total in **invoice list** should include cents (keep values in the bar chart card rounded to dollars)
[x] Add "Unarchive" button for view of archived projects (where the "Edit project" button is now)

### Individual client view

[x] Right-align values in budget, invoiced, uninvoiced columns
[x] Add date started column
[x] Sort projects reverse chronological by date started, within active and archived groups (active at the top)
