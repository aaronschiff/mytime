# Backlog

## Schema migration needed on bbbee.local

New columns and a new table were added. The `_MIGRATIONS` list in `db.py` handles `ALTER TABLE` for existing columns (`invoice_prefix`, `invoice_number`, `client_id`). The new `client` table will be created automatically by `create_all` on first run. After deploying, the startup `_populate_client_ids()` will backfill `client_id` on all existing projects.

## Deferred features for future work

- **Midnight rollover:** Handle timer left running across midnight (currently ticks into next day but doesn't automatically stop or adjust date).
- **Auth & HTTPS:** If app is ever exposed beyond trusted LAN, add authentication (basic auth or OIDC) and enforce HTTPS.
- **CSV export:** Export time entries or invoice history to CSV for accounting/reconciliation.
- **Time-entry templates:** Save and reuse common time-entry descriptions.
- **Bulk invoice operations:** Void or re-lock multiple invoices at once.
- **Dark mode:** UI theme toggle.
