# Backlog

## Data-integrity / reliability

These surfaced during the 2026-06-30/07-01 failure-point audit (see WORKLOG). The five top data-loss risks were fixed; these are the lower-priority remainders.

- **FK enforcement off.** SQLite runs with `foreign_keys=OFF`, so orphaned references are possible — e.g. `delete_client` removes a client while projects still hold its `client_id`. Enabling `PRAGMA foreign_keys=ON` needs an audit of every delete path plus a one-off cleanup of any existing orphans, with tests, before flipping it on. Data-integrity gap, not a direct time-loss risk.
- **Invoice-build under-invoice on bad input (hourly path only).** The hourly invoice builder still does `parse_duration(...) or 0`, so an unparseable per-task duration silently becomes 0 invoiced (under-invoices). Tracked time isn't lost (the `TimeEntry` is preserved), so low priority — fix by mirroring the reject-with-400 pattern now used in the fixed-fee path and in `/time/new` / `/today/add`.
- **No undo/audit for single-entry deletes.** Today-page and time-list delete are hard deletes (guarded only by invoice-lock + JS confirm). Blast radius is one entry, but there's no soft-delete, trash, or audit log. Consider a soft-delete/`deleted_at` column if this ever bites.
- **Off-site SSH hardening (optional).** The off-site backup target's firewall could be tightened: web ports from Cloudflare ranges only, SSH (22) from known IPs only. See `deploy/bbbee.md` (gitignored) for the real target. Optional belt-and-suspenders.
- **Deploy-script fixes live only locally.** `deploy/deploy-bbbee.sh` is gitignored (keeps server specifics out of the public repo) but holds safety-relevant logic — notably `--exclude='mytime.db*'` (so rsync `--delete` can't wipe the live WAL sidecar) and the full `uv` path. Those fixes exist only on the dev machine. Consider a tracked sanitised template (`deploy-bbbee.sh.example`) so the logic is version-controlled.

## Dev-experience / test hygiene

- **Static asset cache-busting.** `app.css` and JS are linked as bare `/static/...` with no version query, so CSS/JS changes silently show stale until a hard refresh — caused confusion twice on 2026-07-02. Add a cache-buster (e.g. `app.css?v=<mtime|hash>`) in `base.html`.
- **Flaky date-dependent test.** `test_time_routes.py::test_create_entry_and_list` hard-codes a 2026-06-25 entry and relies on the real `today()`, so it fails once the real date is >7 days later (default filter window). Freeze the clock in the test (inject `today()`), don't rely on wall-clock date.

## Deferred features for future work

- **Midnight rollover:** A timer left running overnight already appears in today's view (the `running_since IS NOT NULL` clause) and can be stopped normally. The entry retains its original date, which is correct. What's unresolved is *auto-stopping* at midnight if desired.
- **Auth & HTTPS:** If app is ever exposed beyond trusted LAN, add authentication (basic auth or OIDC) and enforce HTTPS. Revisited 2026-07-02 (installed Dock app shows "Not Secure" in the title bar) — user decided against it for now: no easy way to get a trusted cert for a `.local` LAN hostname without extra infra (Tailscale cert, own domain + DNS-01 + reverse proxy, or self-signed + manual per-device trust). Reconsider if Tailscale gets adopted for this LAN.
- **CSV export:** Export time entries or invoice history to CSV for accounting/reconciliation.
- **Time-entry templates:** Save and reuse common time-entry descriptions.
- **Bulk invoice operations:** Void or re-lock multiple invoices at once.
- **Dark mode:** UI theme toggle.
