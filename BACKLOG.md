# Backlog

## Deferred features for future work

- **Midnight rollover:** A timer left running overnight already appears in today's view (the `running_since IS NOT NULL` clause) and can be stopped normally. The entry retains its original date, which is correct. What's unresolved is *auto-stopping* at midnight if desired.
- **Auth & HTTPS:** If app is ever exposed beyond trusted LAN, add authentication (basic auth or OIDC) and enforce HTTPS.
- **CSV export:** Export time entries or invoice history to CSV for accounting/reconciliation.
- **Time-entry templates:** Save and reuse common time-entry descriptions.
- **Bulk invoice operations:** Void or re-lock multiple invoices at once.
- **Dark mode:** UI theme toggle.
