# Backlog

## Code cleanup

- Replace `@app.on_event("startup")` with FastAPI lifespan handler in `mytime/main.py` (deprecated API).
- Remove dead `try/except Exception: pass` around `register_filters()` in `mytime/main.py` (filters always register now).
- Add None-guard (404 response) on `rename_task_type`/`set_active` in `mytime/services/task_types.py` for bad IDs.
- Add HTTP-layer test asserting 4xx on edit/delete of a locked time entry (service layer is tested; router path is not).

## Deferred features for future work

- **Midnight rollover:** Handle timer left running across midnight (currently ticks into next day but doesn't automatically stop or adjust date).
- **Auth & HTTPS:** If app is ever exposed beyond trusted LAN, add authentication (basic auth or OIDC) and enforce HTTPS.
- **CSV export:** Export time entries or invoice history to CSV for accounting/reconciliation.
- **Keyboard shortcuts:** Quick-start/stop timer, quick-add entry, jump between pages (e.g. Ctrl+T for Today, Ctrl+O for Overview).
- **Timer notifications:** Browser notifications when a timer is running (periodic tick or when stopped).
- **Time-entry templates:** Save and reuse common time-entry descriptions.
- **Bulk invoice operations:** Void or re-lock multiple invoices at once.
- **Data backups:** Automated database backups on systemd timer.
- **Dark mode:** UI theme toggle.
