# mytime

A single-user, LAN-only web app for tracking consulting time via live timers and managing per-project billing.

## License and disclaimer

Released under the [MIT License](LICENSE).

This software is provided "as is", without warranty of any kind, express or implied. Use it at your own risk. The author assumes no responsibility or liability for any loss, damage, or other consequence resulting directly or indirectly from the use of this software, including but not limited to data loss, billing errors, or downtime. It was built for a single specific use case and has not been hardened for multi-tenant, public-internet, or business-critical deployment — review the code yourself before relying on it.

## Goals

- Track time against projects using live start/stop timers
- Manage billing: record which time has been invoiced and report uninvoiced time by task type
- Support a solo consulting business with 3–6 active projects at a time
- The app does **not** generate invoice documents; it tracks invoicing state and computes totals

## Stack

- **Backend:** FastAPI, Uvicorn
- **Templating:** Jinja2 with server-rendered HTML
- **Interactivity:** HTMX for in-place edits and live timer display
- **Storage:** SQLite via SQLAlchemy 2.0
- **Testing:** pytest + httpx
- **Deployment:** systemd service on LAN Debian — single user, no auth

## Running locally

### Quick start (empty database)

```bash
uv run uvicorn mytime.main:app --reload
# Visit: http://localhost:8000/today
```

### Local dev/testing instance (with seed data)

A separate instance on port 8001 uses `dev.db` instead of `mytime.db`, so it never touches the production database on `mytime.local`.

**Seed the database** (re-runnable — deletes and recreates `dev.db`):

```bash
uv run python scripts/seed_dev.py
```

This populates ~6 months of realistic data: 3 clients, 6 projects (4 active, 2 archived), 5 task types, 152 time entries, and 5 invoices. Projects include GST-enabled and non-GST variants, over-budget and under-budget scenarios, and both invoiced and uninvoiced work.

**Start the dev server** (code changes reload automatically — no deploy step):

```bash
./dev
```

This starts uvicorn on port 8001, waits until it's up, and opens Safari. Ctrl-C stops the server. Equivalent to:

```bash
MYTIME_DB_URL=sqlite:///dev.db uv run uvicorn mytime.main:app --reload --port 8001
# Visit: http://localhost:8001/today
```

The `--reload` flag watches for source file changes and restarts automatically, so edits are live on the next page refresh.

## Running tests

```bash
uv run pytest -v
```

All tests pass on a clean working tree. Run before committing.

## Deployment

The `deploy/` directory contains systemd unit files for running mytime as a persistent service.

**Recommended layout:**
- Files: `/opt/mytime/`
- Database: `/opt/mytime/mytime.db` (or set `MYTIME_DB_URL` to any SQLite path)
- Timezone: set `MYTIME_TIMEZONE` to a [tz database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) (e.g. `Pacific/Auckland`) if your server runs UTC but you want "today" to reflect your local date. If unset, the server OS timezone is used.
- Service user: `mytime` (create with `sudo useradd --system --no-create-home mytime`)

**Install the service:**
```bash
sudo cp deploy/mytime.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mytime
```

The app binds to all interfaces on port 8000 by default. No authentication layer — intended for trusted LAN use only. Restrict access with a firewall if needed (e.g. `ufw allow from 192.168.0.0/16 to any port 8000`). Served over plain HTTP (no TLS) — browsers show a "Not Secure" indicator; this is a deliberate tradeoff for a LAN-only single-user app (getting a trusted cert for a `.local` hostname isn't practical without extra infra like Tailscale or a reverse proxy + local CA), not an oversight.

**Remote access:** If the deployment host runs [Tailscale](https://tailscale.com), `tailscale serve` can expose the app over HTTPS on a tailnet-only address (not the public internet), gated by tailnet device membership rather than the LAN firewall rule above. This also sidesteps the "Not Secure" warning above, since Tailscale issues a real, auto-renewing HTTPS certificate for tailnet hostnames. No application changes are required — point `tailscale serve` at the existing `localhost:8000` app. Real hostnames/ports for this deployment are not committed to this public repo; see the gitignored `deploy/bbbee.md` for actual values used in production.

### Backups

`deploy/backup.py` (run nightly via `deploy/mytime-backup.{service,timer}`) takes a **transactionally consistent** snapshot using SQLite's online-backup API (safe to run while the app writes; handles WAL correctly — a plain file copy would not), **verifies** it (`PRAGMA integrity_check` + schema query) and exits non-zero discarding any bad file, then applies 28-day tiered retention. Set via env:

- `MYTIME_DB_PATH`, `MYTIME_BACKUP_DIR` — live DB and on-host backup dir (prefer a physically separate disk).
- `MYTIME_OFFSITE_DEST` — optional `user@host:/path` for an off-site rsync-over-SSH copy (key-based, non-interactive). Accumulates history independently of local pruning; an off-site failure is loud but never discards the verified local backup.

The systemd unit **must** set the env vars explicitly — relying on defaults is how a misconfigured unit can silently back up the wrong path.

## Installable app (Dock / Home Screen)

The app is installable as a chrome-less app icon via `mytime/static/manifest.json` and the `<link rel="manifest">` / `apple-touch-icon` / `apple-mobile-web-app-*` tags in `base.html`. No service worker — the app requires the LAN server, so offline caching would add complexity for no benefit; this is manifest + icons only, giving standalone (no address bar) launch.

- **iOS:** Safari → Share → "Add to Home Screen"
- **macOS:** Safari → File → "Add to Dock"
- Point at the production URL (`http://mytime.local:8000/today`) — installing from `localhost:8001` would tie the icon to the dev instance.
- Icons live in `mytime/static/icons/` (180/192/512px + 32px favicon), generated from an ImageMagick MVG source (not committed — regenerate by hand if the design changes) as a blue rounded-square/clock/green-dot mark matching the app's own `--accent`/`--run` colors.
- **Gotcha:** apple-touch-icon PNGs must be fully opaque with **no alpha channel** — if the PNG has any transparency (e.g. from rounded corners baked into the image), iOS/macOS silently reject it and fall back to a generic grey placeholder icon instead of erroring. Generate icons as plain full-bleed squares (`-alpha off -depth 8`); let iOS/macOS apply their own corner rounding.
- Safari caches touch icons aggressively — after changing icon files, remove the existing Dock/Home Screen icon and re-add it to pick up changes.

## Architecture

- **Design principles:** All non-trivial logic in `mytime/services/` as pure functions; templates only for view logic
- **Durations:** Stored as integer seconds; displayed as `HH:MM` (rounded to nearest minute)
- **Money:** `Decimal` throughout (SQLAlchemy `Numeric`), never float
- **Clock:** `mytime.clock.now()` / `today()` wrap datetime for testability. **All stored datetimes are naive UTC** — `now()` returns naive UTC so duration math (`timers.live_elapsed`) is independent of the OS timezone and immune to DST. `today()` is the exception: it honours the `MYTIME_TIMEZONE` env var (a tz database name, e.g. `Pacific/Auckland`) to give the correct *local calendar date* for entry dates and the Today view; falls back to the server OS timezone. `live_elapsed` clamps a backward wall-clock step (never reports/banks less than already-accrued seconds).
- **GST rate:** stored as a percentage value (e.g. `15` = 15%, not `0.15`)

## Data model

| Table | Purpose |
| --- | --- |
| `Client` | First-class client entity (name, unique) |
| `Settings` | Global app defaults (bill rate, currency, default GST rate) |
| `TaskType` | Categories (e.g. "Development", "Research") for grouping time |
| `Project` | Billable projects with budget, bill rate, `client_id` FK, optional GST, and `billing_type` (`hourly`/`fixed`) |
| `TimeEntry` | Individual time records (linked to project + task type) |
| `Invoice` | Invoice headers (project, period, total, optional GST amount, optional `label`) |
| `InvoiceLine` | Line items per task type (tracked vs invoiced seconds, amount) — **not created for fixed-fee invoices** |

`Project` retains the `client_name` text field for display; `client_id` FK is additional metadata. When a client is renamed, all linked project `client_name` fields are updated.

### Billing modes (`Project.billing_type`)

- **`hourly`** (default): invoices are built from tracked time — amount = Σ(invoiced seconds × rate) grouped by task type; creating one **locks** the underlying `TimeEntry` rows. Budget bar shows *invoiced + uninvoiced-time value* vs budget.
- **`fixed`**: for fixed-fee/milestone engagements (e.g. a $45k fee billed in three $15k increments). Invoices are **flat dollar amounts** entered directly (with an optional `label` like "Draft report"), unrelated to time — they create **no `InvoiceLine`s** and **never touch `TimeEntry` rows** (time stays editable). The budget bar instead shows **tracked-time value vs the fee** (an effort/burn measure), with "Invoiced $X of $budget" as text. `hourly_rate` is still used, to value tracked time. Fixed invoices store harmless values in the NOT-NULL `cutoff_date` (= invoice date) and `rate_snapshot` (= project rate); they are distinguished at render time by having no lines. Increments are **not** recorded on the project — you just issue each flat invoice when you reach the milestone.

### Timer mechanics

`TimeEntry` has two fields that work together:
- `seconds` — accumulated seconds from all completed runs
- `running_since` — set to the start datetime while timer is live, `None` when stopped

Live elapsed = `seconds + (now - running_since)`. The `timers.live_elapsed()` service function handles this. Stopping a timer flushes the running delta into `seconds` and clears `running_since`.

### Connection hardening

`db.configure_engine()` registers a `connect` listener that runs `PRAGMA busy_timeout=5000` (wait for locks instead of failing with "database is locked") and `PRAGMA journal_mode=WAL` (concurrent reads during writes, more crash-resilient than the default rollback journal) on every connection. WAL creates `mytime.db-wal` / `mytime.db-shm` sidecar files; the deploy rsync excludes `mytime.db*` so they're never deleted out from under the running app, and backups use the SQLite online-backup API (which handles WAL correctly — a plain file copy would not).

### Schema migrations

`db.py` holds a `_MIGRATIONS` list of `ALTER TABLE` statements. Each is executed with `try/except` on startup (idempotent — fails silently if the column already exists). To add a column: append the SQL to `_MIGRATIONS` **and** add the field to `models.py`. `Base.metadata.create_all` handles new tables; `_MIGRATIONS` handles new columns on existing tables.

## Project layout

```
scripts/
  seed_dev.py       # Populate dev.db with 6 months of dummy data (re-runnable)
dev                 # Shell script: seed check + start dev server on :8001 + open Safari
mytime/
  main.py           # FastAPI app + lifespan (calls init_db)
  db.py             # Engine, session factory, _MIGRATIONS list
  models.py         # SQLAlchemy models (7 tables)
  clock.py          # now(), today() — wrap datetime for test injection
  format.py         # parse_duration, fmt_hm, fmt_hms, money, money_cents, truncate_words
  templating.py     # Jinja2 setup, registers filters (hm, hms, money, date)
  routers/          # One file per feature area; thin — delegate to services
    today.py        # /today — live timers, add/start/stop/set-time/delete
    api_today.py    # /api/today/* — JSON API mirroring today.py, for the menubar app (see below)
    time_entries.py # /time — list, new, edit, delete
    projects.py     # /projects — CRUD, status, delete
    invoices.py     # /invoices and /projects/{id}/invoices/*
    clients.py      # /clients — list, detail, edit, delete
    settings.py     # /settings — defaults, task types
    overview.py     # / — project summary cards
  services/         # Pure business logic, no HTTP concerns
    timers.py       # start/stop/add timer, live_elapsed, todays_timers
    time_entries.py # create/update/delete/list entries
    projects.py     # create/update/set_status/list/get
    budget.py       # project_summary → ProjectSummary dataclass
    invoicing.py    # build preview, create, void, list, GST calc
    settings_service.py
    task_types.py
    clients.py
    guards.py       # delete guards; raises ProjectHasInvoicesError, EntryLockedError, ClientHasTimeError
  templates/
    base.html                  # Nav + layout shell
    today.html                 # Today page (includes _today_body.html)
    _today_body.html           # HTMX swap target (#timers); ctx: rows, total_seconds, names, task_names
    _project_detail_body.html  # Included in project_detail.html; ctx: project, entries, invoices, task_names, currency
    _budget_bar.html           # Included in overview.html and project_detail.html; ctx variable is `s` (ProjectSummary)
    project_detail.html        # ctx includes `s` as alias for summary (used by _budget_bar.html)
    time_entry_form.html       # New + edit form; accepts preset_project_id for pre-selection
    invoice_build.html         # Live-calculating invoice builder with optional GST summary
    [others named for their route]
  static/
    app.css         # All styles
    timer-tick.js   # Runs every second; updates .elapsed spans and total; fmtHms → HH:MM
    htmx.min.js
    manifest.json   # Web app manifest for installable Dock/Home Screen icon
    icons/          # apple-touch-icon.png, icon-192.png, icon-512.png, favicon.png
tests/
  conftest.py       # In-memory SQLite fixture + TestClient with session override
  test_*.py         # 123 tests, all passing (includes test_api_today_routes.py)
deploy/
  mytime.service    # systemd unit (generic /opt/mytime path)
  backup.py         # Consistent + verified DB snapshot; 28-day tiered retention; optional off-site push
```

## Key patterns

### `from_page` redirect
Forms that can be reached from multiple pages pass `from_page` as a hidden input or query param. The router redirects to `from_page` on success, or defaults to a sensible fallback. Cancel buttons use `onclick='location.href=...'` to navigate without submitting.

### HTMX partial reloads (today view)
The today view wraps the timer list in `<div id="timers">`. Start/stop/set-time/delete all POST via HTMX with `hx-target="#timers" hx-swap="innerHTML"` and return just the `_today_body.html` partial — no full page reload.

### Cross-device timer sync (polling + focus refresh)
`GET /today/body` (mytime/routers/today.py) is a read-only route that returns the same `_today_body.html` partial the POST handlers already return — it exists purely so the browser can poll it. `#timers` carries `hx-trigger="every 5s, refresh-timers from:body"`, so it re-fetches on a 5s interval and whenever a `refresh-timers` custom event fires on `<body>`; a `visibilitychange` listener in `today.html` fires that event on tab/app focus, so switching back to the tab syncs instantly instead of waiting up to 5s. A guard (`htmx:beforeRequest` on `#timers`) cancels a poll while an inline elapsed-time edit is open (`.elapsed-edit-form[style*="display:inline"]`), so the swap can't clobber a half-typed value — the next 5s tick retries once the edit closes. `timer-tick.js`'s `htmx:afterSwap` handler intentionally does **not** reset `_notifiedSince` (only `tick()` re-runs) — `_checkNotification` already dedupes on the timer's `since`, so resetting it would make the ">4h still running" notification re-fire on every 5s poll. No server-side push (SSE) — this is poll-based, layerable to SSE later without touching the endpoint or the guard if push is ever added.

### `ProjectSummary` and `s` variable
`budget.project_summary()` returns a `ProjectSummary` dataclass with `invoiced_value`, `uninvoiced_value`, `budget_remaining`, `over_budget`, `exceedance`, `total_tracked_seconds`. In templates it's always bound to `s` (both overview loop variable and `project_detail.html` context key).

### `parse_duration`
`format.parse_duration(str) → int | None`
- Empty string → `0`
- Plain integer (e.g. `"2"`) → hours × 3600
- `"hh:mm"` → seconds; returns `None` if minutes > 59 or non-numeric
- Returns `None` for any other invalid input — callers must handle `None`

### Duration display (`hm` filter)
`fmt_hm` rounds to the nearest minute (adds 30s before dividing), then zero-pads both hours and minutes: `"02:30"` not `"2:30"`. Use `| hm` everywhere. The `| hms` filter (H:MM:SS) exists but is not used in templates.

### CSS utility classes
| Class | Use |
|---|---|
| `btn-save` | Blue filled submit button |
| `btn-cancel` | Grey outlined cancel button |
| `muted` | Secondary/dimmed text (`color: #64748b`) |
| `locked` | Greyed-out invoiced row |
| `running` | Green-highlighted active timer row |
| `seg-inv / seg-unv / seg-rem / seg-over` | Budget bar segments (blue/light-blue/grey/red) |
| `swatch-inv/unv/rem/over` | Matching 10px legend squares |
| `card` | White bordered rounded container |
| `nowrap` | Prevents cell text from wrapping (used on date and client-name cells) |
| `tabnum` | Tabular figures (`font-variant-numeric: tabular-nums`) for dates, times, money in prose |
| `num` | Tabular figures + `text-align: right` for money columns in tables |
| `current` (on `button`) | Dark filled state for active filter buttons (e.g. Active/Archived) |
| `responsive` (on `table`) | Opts a table into the phone layout: below 600px, rows become labelled cards using each `<td>`'s `data-label` attribute instead of a header row |
| `actions` (on `td`) | Marks a table's trailing button-cell so the phone card layout omits its (non-existent) label and lets buttons wrap |
| `table-scroll` (on wrapper `div`) | `overflow-x: auto` escape hatch for the two tables left un-stacked (`invoice_view.html`, `invoice_build.html` line items) if they overflow at phone width |
| `nav-links` / `nav-toggle` / `nav-toggle-btn` | Hamburger nav below 600px: CSS-only checkbox-toggle (`#nav-toggle:checked ~ .nav-links`), no JS. Desktop/tablet always shows `.nav-links` inline and hides the toggle |

## Features

- **Today page:** Live timer with start/stop; two-mode add (auto-start or save with time); click-to-edit elapsed time (HH:MM); keyboard shortcuts: `s` stop/start, `n` focus new-entry form. Layout: "Total today" below h1, "Create timer" card with form, "Today's time entries" table, shortcuts hint at bottom.
- **Projects:** CRUD with budget tracking; archive/unarchive; guarded delete; GST toggle per project; **billing type (hourly / fixed fee)**; client+project name uniqueness enforced; archived projects: Edit hidden, Unarchive shown; blocked from new time entries and invoices; projects list sorted reverse-chronological with date-started column
- **Time entries:** Log manual entries (hh:mm or plain hours); edit/delete guarded by invoice lock and project archived status; future-date confirmation; ≥10h entry confirmation; notes truncated to 3 words in all list views; date filter buttons (Last 7 days / Last 30 days / All, default 7d) with 30-entry pagination; pagination uses HTMX in-place swap (no full page reload)
- **Invoicing (hourly):** Build per project, group by task type, live dollar amounts with cents; GST rows in table footer when enabled; auto-suggested numeric invoice numbers; void blocked for archived projects; invoice list in project detail shows cents
- **Invoicing (fixed fee):** Flat-amount form (amount + optional label + date + number) with live GST; rejects a missing/non-numeric amount with a 400; creates no lines and leaves tracked time untouched; invoice lists show the label column
- **Invoice view:** Amount column right-aligned; all values show cents
- **Invoice list:** `/invoices` — all invoices reverse-chronological
- **Overview:** Project cards with budget bar; over-budget in red with exceedance; remaining shown with percentage
- **Clients:** List with project count and total invoiced; detail with Archive/Delete per project; rename propagates to all linked projects; projects sorted active-first then reverse-chronological; date-started column
- **Settings:** Default hourly rate, currency symbol, default GST rate, task type management

## Menubar JSON API (backend)

`mytime/routers/api_today.py` is the backend half of the native macOS menubar widget (`MenuBarExtra`, SwiftUI) mirroring the Today page — see "Menubar app (frontend)" below for the client. It's a thin JSON wrapper over the same `mytime/services/*` functions `today.py` already uses: no new business logic, no auth (same LAN-only trust model as the rest of the app).

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/today` | Full state: day, total/week seconds, active projects, active task types, entries |
| POST | `/api/today/entries` | Create entry — start now, or save with a duration |
| POST | `/api/today/{id}/start` | Start (stops any other running timer — same server-enforced single-running-timer invariant as the web app) |
| POST | `/api/today/{id}/stop` | Stop |
| POST | `/api/today/{id}/set-time` | Quick inline elapsed-time edit (stopped entries only) |
| POST | `/api/today/{id}/edit` | Full edit: project/task type/duration/notes — no `entry_date` (moving an entry to a different day stays a Time-page-only, web-app action) |
| DELETE | `/api/today/{id}` | Delete |

Every mutation endpoint — including create and delete — returns the same full `GET /api/today` shape on success, so a client can always replace its local state wholesale from any response rather than tracking a separate shape per action. Errors are always `{"error": "..."}` (400 bad duration, 403 locked entry/archived project, 404 unknown id) via a shared `_error()` helper — never FastAPI's default `{"detail": ...}` shape — with one accepted asymmetry: a malformed/missing JSON body field (e.g. non-integer `project_id`) falls through to FastAPI's own default 422 response, not the router's own 400/`{"error"}` shape (a documented, deliberate scope cut, not a bug — worth noting for the eventual Swift client).

Cross-device sync reuses the same polling pattern already built for the web app (see "Cross-device timer sync" above) — no new mechanism, no SSE/push; the menubar client polls `GET /api/today` and always does a full-state replace.

## Menubar app (frontend)

`MyTimeMenuBar/` (repo root) is a native macOS `MenuBarExtra` (SwiftUI, macOS 14+) client for the `/api/today` backend. Key features and design decisions:

- **Full parity with the web Today view** — list, add, start/stop, click-to-edit elapsed, full edit, delete — plus a menubar icon with live-ticking `H:MM` elapsed time.
- **One icon rule throughout:** a green dot always means "running," a stop/play glyph always means "what clicking this does." The menubar icon is an uncolored stop-square when idle (most-recently-run entry's elapsed, or `0:00`) and a green dot when active. Each row shows a green dot left of its name only while running (a same-size clear spacer otherwise, so the name never shifts) and a play/stop toggle left of its elapsed time.
- **Clicking anywhere on the icon/time opens the dropdown** — no click-splitting (descoped; would need a hand-rolled `NSStatusItem`).
- **No Dock icon** (`LSUIElement`).
- **Server URL is the only setting** (`@AppStorage`, default `http://mytime.local:8000`), edited via a small AppKit-managed, **non-modal** settings window with Save/Cancel (`SettingsWindowController` in `SettingsView.swift`; a true app-modal version was tried and reverted — see quirks below).
- **Two background loops in `TimerStore`:** a 1s display tick (recomputes elapsed from `base_seconds + (now - since)`, never a local counter) and a ~20s sync poll (full-state replace, catches web/other-device changes).
- **Silent sync failures, with one exception:** the poll stays quiet for most errors (the banner is for user actions), but "can't reach the server" (`APIError.connectivity`) always surfaces and is not user-dismissable — it clears itself the instant any request succeeds again (next poll, or immediately after fixing the address in Settings, which restarts the sync loop). This keeps a dead/wrong address visible without user action and avoids a stale banner lingering after the server returns.
- **4-hour overrun alert** via `UNUserNotificationCenter`, deduped on the entry's `since`. Threshold is checked against the *current continuous run* (`now - since`), not the entry's cumulative total across earlier stop/restart cycles — matches the web app's `timer-tick.js` reference behavior.
- **Shared enum-based keyboard focus** (`FocusTarget` in `ContentView.swift`, threaded through `EntryRow`/`AddEntryForm`/`EntryEditForm` via `@FocusState.Binding`): pressing Esc in a field returns focus to `.container` (the dropdown root) so a second Esc always has a responder and never falls through to the system beep. Esc does **not** dismiss the dropdown itself (see quirks below) — it only cancels an open row edit or defocuses a field.

App Sandbox is off (`ENABLE_APP_SANDBOX = NO`): the Xcode macOS App template enables it by default with no entitlements, which silently blocks all outgoing network connections, including to `localhost`; this personal LAN utility (Personal Team signing, never App Store) has no need for it.

Platform quirks worth knowing if touching this code:
1. SwiftUI's `Settings` scene / `openSettings()` reliably fails to present a window for `MenuBarExtra`-only (LSUIElement) apps — hence the AppKit-based `SettingsWindowController` workaround.
2. System-level presentations in general (`.confirmationDialog`, likely `.alert`/`.sheet` too) can leave `MenuBarExtra`'s special window stuck/invisible after dismissal — the delete confirmation in `EntryRow` uses an inline confirm (Delete? / ✓ / ✕) instead, never a system dialog.
3. `MenuBarExtra` always renders its label's SF Symbol images as forced "template" (monochrome, auto-tinted) images — neither SwiftUI's `.foregroundStyle()` nor `.renderingMode(.original)` can override this (confirmed via [Apple Developer Forums thread 738716](https://developer.apple.com/forums/thread/738716)). A genuinely colored icon (the running-state green dot) requires bypassing `Image(systemName:)` and building an `NSImage` directly with an explicit `NSImage.SymbolConfiguration(paletteColors:)` and `isTemplate = false` — see `statusIcon` in `MyTimeMenuBarApp.swift`. Because the two icon states are built two different ways (raw `NSImage` for running, plain `Image(systemName:)` for idle), `statusIcon`'s return type is `some View` (not `Image`) with a `.font()` call applied unconditionally on both branches at the end — Swift's opaque-return-type checker requires every return path to produce the same concrete type, so the modifier chain has to match even though it's a no-op on the pre-sized `NSImage` branch. Icon sizes are defined relative to the 13pt menu-bar text baseline (`baseIconPointSize`): the running dot renders at 70% (30% smaller) and the idle square at 90% (10% smaller) — tune `runningIconPointSize`/`idleIconPointSize` if the balance looks off. The time text carries a small `.offset(y:)` to correct it sitting optically high next to the icon (currently 2pt).
6. In this same `.window`-style popup, clicking on empty space (not on an actual control) does **not** change SwiftUI `FocusState` at all — unlike Esc, which explicitly resets it. `EntryRow`'s inline elapsed-time editor originally relied on a `FocusState` change to detect "clicked away, close the editor," which silently never fired for a plain outside click. Fixed with a `.contentShape(Rectangle()).onTapGesture { ... }` catcher on `ContentView`'s root view, which closes it on any tap that isn't claimed by a control first — a mechanism independent of AppKit focus/first-responder state, so it isn't affected by this quirk.
4. There's no supported way to programmatically dismiss a `.window`-style `MenuBarExtra` popup the way a real user click does ([Apple Feedback FB11984872](https://github.com/feedback-assistant/reports/issues/383)): closing/hiding it via any `NSApp`-level call (`NSApp.keyWindow?.close()`, `NSApp.hide(nil)`) leaves the status-item icon stuck in its highlighted state, requiring an extra click to reopen the dropdown. Separately, entering `NSApp.runModal` (e.g. for a true-modal Settings dialog) hides the *entire* dropdown for the modal's duration with no supported way to bring it back afterward. Both of these are why Esc-to-dismiss-the-window and true-modal Settings were tried and then reverted (2026-07-06) — see `docs/superpowers/specs/2026-07-06-menubar-polish-1-design.md` and the WORKLOG entry for that date.
5. Calling `NSApp.activate(ignoringOtherApps: true)` when the app is already active (e.g. from a click already happening inside the app's own frontmost window) can trigger an activation-cycle side effect that closes other windows of the app — this was removed from `SettingsWindowController.show()` after it was found to be closing the main dropdown whenever Settings' Save/Cancel ran.

The Xcode project itself (`.xcodeproj`, signing with a free Personal Team, `LSUIElement`, and the `NSAllowsLocalNetworking` ATS exception for plain-HTTP LAN access) is set up by hand in the Xcode GUI; the `.swift` sources are edited directly (via the Xcode MCP tool in this session, which also drove `BuildProject`/`GetBuildLog` verification after every change). No XCTest target — the two Foundation-only files (`Models.swift`, `APIClient.swift`) have CLI smoke-checks via `swiftc`; the SwiftUI runtime was verified by building and interactively testing in Xcode. Design spec: `docs/superpowers/specs/2026-07-03-menubar-swiftui-app-design.md`; plan: `docs/superpowers/plans/2026-07-05-menubar-swiftui-app.md`.

**Standalone build/run (no Xcode needed):** `MyTimeMenuBar/build.sh [Debug|Release]` runs `xcodebuild` with `-derivedDataPath build` (kept local to the project dir, gitignored) and then relaunches the built `.app` (`killall MyTimeMenuBar` first, so re-running always picks up the latest build). Output lands at `MyTimeMenuBar/build/Build/Products/<Debug|Release>/MyTimeMenuBar.app` — double-clickable in Finder too. Existing Apple Development signing (Personal Team) carries over from the Xcode project settings, so no extra signing setup is needed.

## Responsive phone layout

A single `@media (max-width: 600px)` block in `app.css` reflows the app for phone widths (tested down to an iPhone 13 mini, ~375px CSS width); everything at 600px+ is byte-for-byte the pre-existing desktop/tablet layout. No JS added.

- **Nav:** collapses to a `☰` button behind a CSS-only checkbox toggle (see `nav-links`/`nav-toggle` in the class table above). Navigating away reloads the page, which resets the checkbox, so the menu always closes on link tap.
- **Tables:** any table with `class="responsive"` restacks each row into a labelled card (`<td data-label="…">` supplies the label via a `::before` pseudo-element instead of the hidden `<thead>`). Applied to the main data tables (projects, clients, time entries, invoices list, task types, today's timers). The two narrower totals/build tables (`invoice_view.html`, `invoice_build.html`) keep their normal tabular layout and are wrapped in `.table-scroll` instead, since stacking a 4-column money table reads worse than letting it scroll.
- **Touch targets:** `button`/`input`/`select`/`textarea` get `min-height: 2.5rem` and `font-size: 16px` — the 16px is required, not cosmetic: iOS Safari auto-zooms the page on focus if an input's font-size is below 16px.
- **Inputs:** capped to `max-width: 100%` so template-level inline `style="width:20em"` etc. can't force horizontal overflow.
- **Button appearance:** the base `button` rule (not just the mobile media query) sets `-webkit-appearance:none; appearance:none;` plus an explicit `color`. Without this, mobile Safari/Chrome overlay their native button chrome (a gradient/tint) on top of the custom `background`, which washed out enabled buttons (e.g. "Add & start" on the Today page looked disabled even though it wasn't) and made button text colour inconsistent between mobile and desktop.

## Key constraints

- Single user, no authentication — deploy on trusted LAN only
- SQLite; no migration framework — use `_MIGRATIONS` in `db.py` for schema changes
- All time in seconds internally; display as HH:MM rounded to nearest minute
- All money as `Decimal`; no floating-point arithmetic
- GST rates stored as percentages (e.g. `15` not `0.15`)

## Repository

https://github.com/aaronschiff/mytime
