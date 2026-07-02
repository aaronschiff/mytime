# Backlog

## Data-integrity / reliability

These surfaced during the 2026-06-30/07-01 failure-point audit (see WORKLOG). The five top data-loss risks were fixed; these are the lower-priority remainders.

- **FK enforcement off.** SQLite runs with `foreign_keys=OFF`, so orphaned references are possible — e.g. `delete_client` removes a client while projects still hold its `client_id`. Enabling `PRAGMA foreign_keys=ON` needs an audit of every delete path plus a one-off cleanup of any existing orphans, with tests, before flipping it on. Data-integrity gap, not a direct time-loss risk.

## Deferred features for future work

- **Auth & HTTPS:** If app is ever exposed beyond trusted LAN, add authentication (basic auth or OIDC) and enforce HTTPS. Revisited 2026-07-02 (installed Dock app shows "Not Secure" in the title bar) — user decided against it for now: no easy way to get a trusted cert for a `.local` LAN hostname without extra infra (Tailscale cert, own domain + DNS-01 + reverse proxy, or self-signed + manual per-device trust). Reconsider if Tailscale gets adopted for this LAN.
- **macOS menubar widget (Swift/SwiftUI):** Native `MenuBarExtra` app (macOS 13+) mirroring the Today view — list today's timers, add entry, start/stop, click-to-edit elapsed time, delete; show live-ticking elapsed in the menubar title. Effort ~a weekend, split in two:
  - **Backend (~half day):** Add a parallel JSON API (e.g. `/api/today`) — a thin router over the existing pure service functions, no change to the HTMX views. Everything the Today view needs is already a one-liner: list → `timers.todays_timers()` + `timers.live_elapsed()`; add → `timers.add_timer()` / `te.create_entry()`; start/stop → `timers.start_timer()` / `stop_timer()`; set-time → inline logic in `today.py`; delete → `te.delete_entry()`. Reuse the context shape from `today.py:_context`. This is the cheap, fully-testable half. **Do this first** regardless of the frontend.
  - **Frontend (~1–2 days):** SwiftUI `MenuBarExtra` app — ~4–6 files (Codable models, small `URLSession` API client, view model, menubar view). Modern Swift: `async/await`, `@Observable`/`@State`. Client can be naive about the single-running-timer invariant (enforced server-side in `stop_all_running`). Live ticking = a 1s client-side timer re-rendering `live_elapsed` math (same as `timer-tick.js`).
  - **Notes / caveats:**
    - **Signing:** free Apple ID is enough for personal use (Xcode "Personal Team"); no paid $99 account needed unless distributing to other Macs or the App Store. Free-cert 7-day expiry is a non-issue for a self-built Mac app (only bites iOS sideloading).
    - **Reachability:** widget points at `bbbee.local:8000` on the LAN — dead off-LAN unless on Tailscale/VPN. Decide if that matters.
    - **No auth** on the backend is fine; widget just POSTs to the same open LAN endpoints.
    - The real cost is learning **Xcode** (project setup, signing, build/run — user must drive the GUI) more than Swift the language. Assistant can write all the Swift but can't compile/run it here, so the loop is: write → user builds in Xcode → paste errors → fix.
  