# mytime

A single-user, LAN-only web app for tracking consulting time via live timers and managing per-project billing.

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

A separate instance on port 8001 uses `dev.db` instead of `mytime.db`, so it never touches the production database on `bbbee.local`.

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

The app binds to all interfaces on port 8000 by default. No authentication layer — intended for trusted LAN use only. Restrict access with a firewall if needed (e.g. `ufw allow from 192.168.0.0/16 to any port 8000`).

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
| `Project` | Billable projects with budget, bill rate, `client_id` FK, and optional GST |
| `TimeEntry` | Individual time records (linked to project + task type) |
| `Invoice` | Invoice headers (project, period, total, optional GST amount) |
| `InvoiceLine` | Line items per task type (tracked vs invoiced seconds, amount) |

`Project` retains the `client_name` text field for display; `client_id` FK is additional metadata. When a client is renamed, all linked project `client_name` fields are updated.

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
tests/
  conftest.py       # In-memory SQLite fixture + TestClient with session override
  test_*.py         # 53 tests, all passing
deploy/
  mytime.service    # systemd unit (generic /opt/mytime path)
  backup.py         # 28-day tiered DB snapshot script
```

## Key patterns

### `from_page` redirect
Forms that can be reached from multiple pages pass `from_page` as a hidden input or query param. The router redirects to `from_page` on success, or defaults to a sensible fallback. Cancel buttons use `onclick='location.href=...'` to navigate without submitting.

### HTMX partial reloads (today view)
The today view wraps the timer list in `<div id="timers">`. Start/stop/set-time/delete all POST via HTMX with `hx-target="#timers" hx-swap="innerHTML"` and return just the `_today_body.html` partial — no full page reload.

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

## Features

- **Today page:** Live timer with start/stop; two-mode add (auto-start or save with time); click-to-edit elapsed time (HH:MM); keyboard shortcuts: `s` stop/start, `n` focus new-entry form. Layout: "Total today" below h1, "Create timer" card with form, "Today's time entries" table, shortcuts hint at bottom.
- **Projects:** CRUD with budget tracking; archive/unarchive; guarded delete; GST toggle per project; client+project name uniqueness enforced; archived projects: Edit hidden, Unarchive shown; blocked from new time entries and invoices; projects list sorted reverse-chronological with date-started column
- **Time entries:** Log manual entries (hh:mm or plain hours); edit/delete guarded by invoice lock and project archived status; future-date confirmation; ≥10h entry confirmation; notes truncated to 3 words in all list views; date filter buttons (Last 7 days / Last 30 days / All, default 7d) with 30-entry pagination; pagination uses HTMX in-place swap (no full page reload)
- **Invoicing:** Build per project, group by task type, live dollar amounts with cents; GST rows in table footer when enabled; auto-suggested numeric invoice numbers; void blocked for archived projects; invoice list in project detail shows cents
- **Invoice view:** Amount column right-aligned; all values show cents
- **Invoice list:** `/invoices` — all invoices reverse-chronological
- **Overview:** Project cards with budget bar; over-budget in red with exceedance; remaining shown with percentage
- **Clients:** List with project count and total invoiced; detail with Archive/Delete per project; rename propagates to all linked projects; projects sorted active-first then reverse-chronological; date-started column
- **Settings:** Default hourly rate, currency symbol, default GST rate, task type management

## Key constraints

- Single user, no authentication — deploy on trusted LAN only
- SQLite; no migration framework — use `_MIGRATIONS` in `db.py` for schema changes
- All time in seconds internally; display as HH:MM rounded to nearest minute
- All money as `Decimal`; no floating-point arithmetic
- GST rates stored as percentages (e.g. `15` not `0.15`)

## Repository

https://github.com/aaronschiff/mytime
