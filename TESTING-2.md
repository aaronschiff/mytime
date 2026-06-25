# Mytime user testing round 2

## Bugs

[x] Clicking Edit on a running timer from the today view loses the tracked time
[x] Edit time entry does not give an error if an invalid time is entered (e.g. text)
[x] Time entries of archived projects should not be editable
[x] Invoices should not be able to be created or voided for archived projects
[x] Clicking "New time entry" from a project view should pre-select that project in the project dropdown on the new time entry form
[x] Adding or editing a time entry with an invalid numeric time (e.g. 3:66) creates a 0:00 time entry; should give an error

## New features

### GST

[x] Add a default GST (sales tax) rate to settings (always a percentage)
[x] Add a toggle when creating or editing projects that allows GST to be selected for the project
[x] If GST is selected for a project, prefill it with the default rate but allow it to be edited
[x] When generating invoices for projects that have GST enabled: 
    - Show the total excluding GST
    - Show the GST amount
    - Show the total including GST

## UI polish

### General 

[x] "Cancel" should always be a button, not a hyperlink
[x] Visually distinguish "Save" and "Cancel" buttons
[x] Drop "Invoice number prefix" from settings and invoicing -- invoice numbers can just be numeric
[x] If a time entry is added or edited anywhere, if the user just enters a number with no ":" separator (e.g. "2"), it should be interpreted as hours with zero minutes (e.g. "2:00")
[x] Times should always display with two digits for hours and two digits for minutes, e.g. "02:30", not "2:30"

### Edit project view 

[x] Hourly rate and Budget should display dollars only (no cents)

### Settings

[x] Put each setting under "Defaults" on its own line, don't float horizontally

### New project form

[x] Description text field font size should be the same as other fields
[x] Hourly rate field should display only dollars

### Project list view

[x] Remove the rate column, budget, invoiced and uninvoiced total columns to the project rows

### Project list for a client

[x] Add Archive and Delete buttons (same as the main project list)
[x] Remove the rate column, budget, invoiced and uninvoiced total columns to the project rows

### Today view

[x] Total today should just show hh:mm (no seconds)
[x] Active timer should just show hh:mm (no seconds)

### Time entries list view

[x] Truncate notes with "..." if they are longer than a few words

### Overview view

[x] Over budget section of the bar chart should be red (matching the label)
[x] If remaining budget is > 0, show the percentage of the budget remaining in brackets next to the dollar amount

### Clients view

[x] Add "Total invoiced" column for each client

### Invoice view

[x] "Void invoice" needs a little top margin

