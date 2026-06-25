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

```bash
# Start the server with auto-reload
uv run uvicorn mytime.main:app --reload

# Then visit: http://localhost:8000/today
```

## Running tests

```bash
# Run all tests with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_settings.py -v
```

All tests pass on a clean working tree. Run before committing.

## Deployment

### Current deployment: `bbbee.local`

Running on `bbbee.local` (Ubuntu Linux, x86_64) as user `aaron`.

- Files: `/home/aaron/mytime/`
- Database: `/home/aaron/mytime/mytime.db`
- `uv`: `/home/aaron/.local/bin/uv`
- Systemd unit: `/etc/systemd/system/mytime.service` (enabled, starts on boot)
- URL: **http://bbbee.local:8000/today**
- Firewall: ufw allows port 8000 from `192.168.1.0/24` only

To redeploy after changes:
```bash
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache' --exclude='*.db' --exclude='.env' . bbbee.local:~/mytime/
ssh bbbee.local 'cd ~/mytime && /home/aaron/.local/bin/uv sync && sudo systemctl restart mytime'
```

### Generic LAN server setup

The `deploy/mytime.service` unit file uses `/opt/mytime` and a dedicated `mytime` user. Adapt paths and `User=` for your target. Key steps: install `uv`, rsync files, rebuild venv with `uv sync`, install unit, open the firewall port for LAN.

The app binds to all interfaces on port 8000. No authentication layer — assume the network is trusted.

## Architecture

- **Design principles:** All non-trivial logic in `mytime/services/` as pure functions; templates only for view logic
- **Durations:** Stored as integer seconds; display as hours:minutes
- **Money:** `Decimal` throughout (SQLAlchemy `Numeric`), never float
- **Clock:** `mytime.clock.now()` / `today()` wrap datetime for testability
- **Deployment target:** Systemd service on Debian, LAN-only, sqlite:////opt/mytime/mytime.db

## Data model

| Table | Purpose |
| --- | --- |
| `Settings` | Global app defaults (bill rate, invoice prefix) |
| `TaskType` | Categories (e.g. "Development", "Research") for grouping time |
| `Project` | Billable projects with assigned budget and bill rate |
| `TimeEntry` | Individual time records (linked to project + task type) |
| `Invoice` | Invoice headers (project, period, total) with lock/void state |
| `InvoiceLine` | Line items per task type (with applied second adjustments) |

## Project layout

```
mytime/
  main.py                    # FastAPI app, startup
  db.py                      # SQLAlchemy engine, session factory
  models.py                  # SQLAlchemy models (6 tables)
  clock.py                   # now(), today() (testable)
  format.py                  # formatters: hm, hms, money
  templating.py              # Jinja2 setup + filters
  routers/                   # HTTP endpoints
  services/                  # Pure business logic
    settings_service.py
    task_types.py
    projects.py
    time_entries.py
    timers.py
    budget.py
    invoicing.py
    guards.py
  templates/                 # Jinja2 templates
  static/                    # CSS, JavaScript (HTMX, timer-tick.js)
tests/
  conftest.py                # pytest fixtures
  test_*.py                  # Unit + integration tests (43 tests, all passing)
deploy/
  mytime.service             # systemd unit file
```

## Repository

https://github.com/aaronschiff/mytime (private)

## Design spec

Full product design and API spec:  
[docs/superpowers/specs/2026-06-25-mytime-time-tracking-billing-design.md](docs/superpowers/specs/2026-06-25-mytime-time-tracking-billing-design.md)

## Features

- **Today page:** Live timer with start/stop buttons; auto-stop when adding new entry; running timer visible at top
- **Projects:** CRUD with budget tracking; archive projects; guarded delete (cannot delete if has entries)
- **Time entries:** Log manual entries; edit/delete (guarded by invoice lock)
- **Invoicing:** Build invoice per project, group by task type, apply per-task adjustments, lock/void
- **Overview:** Landing page with project cards showing budget remaining, uninvoiced time by task type
- **Settings:** Global rate, invoice prefix, task type management

## Key constraints

- Single user, no authentication — deploy on trusted LAN only
- Systemd unit runs as `mytime` user, watches service for auto-restart
- SQLite database; no migration tooling (schema in `models.py`)
- All time in seconds internally; display as hours:minutes
- All money as `Decimal`; no floating-point arithmetic
