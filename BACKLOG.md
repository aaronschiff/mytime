# Backlog

## Schema migration needed on bbbee.local

New GST columns were added in this session. The `_MIGRATIONS` list in `db.py` handles `ALTER TABLE` for all new columns (`settings.default_gst_rate`, `project.gst_enabled`, `project.gst_rate`, `invoice.gst_amount`). These run automatically on startup — just deploy and restart the service.

## Deferred features for future work

- **Midnight rollover:** Handle timer left running across midnight (currently ticks into next day but doesn't automatically stop or adjust date).
- **Auth & HTTPS:** If app is ever exposed beyond trusted LAN, add authentication (basic auth or OIDC) and enforce HTTPS.
- **CSV export:** Export time entries or invoice history to CSV for accounting/reconciliation.
- **Time-entry templates:** Save and reuse common time-entry descriptions.
- **Bulk invoice operations:** Void or re-lock multiple invoices at once.
- **Dark mode:** UI theme toggle.
