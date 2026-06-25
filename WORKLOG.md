# Worklog

## 2026-06-25

**What we worked on:** Full TESTING.md pass — all bugs, backlog items, and new features resolved; 53 tests passing.

- Worked through every item in `TESTING.md`; all marked `[x]`.
- **UTC timer bug:** Timers showed 12h offset because `running_since.isoformat()` emits a naive datetime string; fixed by appending `"Z"` so `Date.parse()` in `timer-tick.js` treats it as UTC.
- **JS total bug:** Stopped timer `<span>` elements lost the `.elapsed` class in a refactor, so `timer-tick.js` no longer included them in the daily total. Fixed by restoring `.elapsed elapsed-display` dual-class with `data-running="0"` on stopped entries and updating `timer-tick.js` to only set `textContent` for running timers.
- **Keyboard shortcuts:** Added `s`/`S` (stop/start timer) and `n`/`N` (focus add-form) in `today.html`; guards against active input elements.
- **Browser notifications:** `_checkNotification()` added to `timer-tick.js`; triggers once when running timer exceeds 4 hours since last start; requests permission on first tick.
- **Data backups:** `deploy/backup.py` with 28-day tiered retention (daily snapshots for 28 days, then one per 28-day window); `deploy/mytime-backup.service` + `deploy/mytime-backup.timer` systemd units.
- **Clients feature:** See prior entry below for full detail.
- Caught and removed `</content>` XML artefacts introduced by subagents into Python files and templates.

---

## 2026-06-25

**What we worked on:** Clients feature — first-class Client entity, Clients page, CRUD with delete guard.

- Added `Client` model (id, name unique, created_at) to `models.py`; added nullable `client_id` FK on `Project`.
- Added `ALTER TABLE project ADD COLUMN client_id INTEGER REFERENCES client(id)` migration to `db.py._MIGRATIONS`.
- Added `_populate_client_ids()` in `db.py` called from `init_db()` after migrations — looks up or creates `Client` records for all existing projects whose `client_id IS NULL`.
- Created `mytime/services/clients.py`: `list_clients`, `get_client`, `create_client`, `update_client` (also updates all linked project `client_name` fields), `delete_client` (raises `ClientHasTimeError` if blocked), `find_or_create`.
- Added `ClientHasTimeError` and `can_delete_client()` to `mytime/services/guards.py`.
- Updated `mytime/services/projects.py` `create_project` and `update_project` to call `find_or_create` and set `client_id` on the project.
- Created `mytime/routers/clients.py` with: `GET /clients`, `GET /clients/{id}`, `GET /clients/{id}/edit`, `POST /clients/{id}/edit`, `POST /clients/{id}/delete`.
- Created three templates: `clients.html` (list with project count), `client_detail.html` (per-client project list), `client_form.html` (name-only edit form).
- Added `<a href="/clients">Clients</a>` to `base.html` nav between Time and Invoices.
- Registered clients router in `main.py`.
- All 53 existing tests continue to pass — no new test fixtures needed; `create_all` in conftest includes new `Client` table and `client_id` column automatically.
- Marked all Clients items, Keyboard shortcuts, Browser notifications, Data backups, and all UI polish items as `[x]` in `TESTING.md`.

---

## 2026-06-25

**What we worked on:** Full UI polish pass from TESTING.md — all items implemented, 53 tests passing.

- Implemented all UI polish items from `TESTING.md` in one session; all checkboxes now marked `[x]`.
- **app.css:** Removed pulsing animation from running timer dot (now solid green). Added spinner-hiding CSS for number inputs. Added `.over-budget` red class and `.swatch` + `.swatch-inv/unv/rem` for legend swatches.
- **format.py:** Added `parse_duration(hm: str) -> int` helper (parses "hh:mm" → seconds, returns 0 for invalid).
- **Today page:** (1) Solid dot. (2) Invoiced entries show "Invoiced" label instead of Start/Edit/Delete. (3) Two-mode add — duration input + JS toggles button from "Add & start" to "Save" and sets `start` hidden field; `POST /today/add` routes to `add_timer` vs `create_entry`. (4) Click-to-edit elapsed time on stopped entries; `POST /today/{id}/set-time` endpoint updates seconds in place.
- **Time entry form:** Replaced `hours` + `minutes` number inputs with single `duration` text field (hh:mm). Notes textarea full-width. Future-date confirm dialog via JS. `from_page` param threads cancel/save redirect back to caller.
- **Project form:** Full-width fields, description 4 rows, currency symbol prefix on rate/budget, `<datalist>` autocomplete for client name from existing projects, `from_page` param for cancel/save.
- **Overview:** Colored swatches before Invoiced/Uninvoiced/Remaining labels, over-budget amount in `.over-budget` red, "New invoice" link per project card.
- **Invoice build page:** Replaced h+m number inputs with single hh:mm text field per task row. Added dollar amount column (calculated live by JS). Added totals row (tracked, invoiced, dollars). Showed already-invoiced total and budget remaining (from budget service). Added editable `invoice_number` field with uniqueness check (returns 400 with error message on duplicate). Invoice number prefix sourced from `Settings.invoice_prefix`.
- **Invoice model:** Added nullable `invoice_number` column (String(50)). Note: existing DBs need column added manually or DB recreated.
- **Settings model + service + router:** Added `invoice_prefix` field (String(20), default "INV-"). Settings page shows/saves it.
- **Invoice list:** New `GET /invoices` endpoint + `invoice_list.html` template (reverse-chron, shows number, project, dates, total). Added "Invoices" nav link between "Time" and "Settings" in `base.html`. Invoice view title uses `invoice_number` if set.
- **Projects list:** Active/Archived filter links visually highlighted (bold + underline) when selected. `status` passed to template. Edit link converted to button form with `from_page`.
- **Time list:** Edit link converted to button form with `from_page`. "+ New entry" also button form.
- **Tests:** Updated `test_time_routes.py` and `test_invoices_routes.py` for new `duration` / `duration_<tid>` params. Updated `test_smoke.py` to use `client` fixture (was using real DB, broke on new column). Added `test_format.py::test_parse_duration`. Added `tests/test_new_features.py` with 7 new tests covering save-without-start, set-time, invoice list, invoice number uniqueness, and projects status display. Total: 53 tests, all passing (was 45).
- **Key constraint note:** SQLite `create_all` on startup only creates new tables, not new columns — `invoice_prefix` and `invoice_number` columns won't appear in existing DBs without recreation or manual `ALTER TABLE`.

---

## 2026-06-25

**What we worked on:** Deployed to `bbbee.local` for LAN testing.

- Rsync'd project files to `/home/aaron/mytime/` on `bbbee.local` (Ubuntu Linux, x86_64).
- Installed `uv` on the server (`/home/aaron/.local/bin/uv`); rebuilt venv for Linux from `uv.lock` (macOS venv can't be reused).
- Adapted the systemd unit from the repo (`deploy/mytime.service`) to run as `aaron` user at `/home/aaron/mytime/` with DB at `/home/aaron/mytime/mytime.db`; installed at `/etc/systemd/system/mytime.service`, enabled on boot, started.
- Port 8000 was blocked by ufw — added `ufw allow from 192.168.1.0/24 to any port 8000` (LAN-only, matching existing service rules on this host).
- App accessible at `http://bbbee.local:8000/today`.

---

## 2026-06-25

**What we worked on:** Full 10-task build executed via subagent-driven development; pushed to GitHub.

- Executed all 10 tasks from `docs/superpowers/plans/2026-06-25-mytime.md` using parallel subagents with per-task review gates.
- One Critical finding caught during review (Task 7): `stop_timer` was missing `guards.ensure_unlocked` — patched in a fix commit before marking task complete.
- Final Opus whole-branch review returned "Ready to merge" with no Critical or Important issues.
- Pushed to private GitHub repo: https://github.com/aaronschiff/mytime
- 43 tests passing; 3 pre-existing deprecation warnings from FastAPI `on_event` (plan-mandated, minor).
- Minor deferred: replace `@app.on_event("startup")` with lifespan handler; remove dead `try/except` around filter registration in `main.py`; add None-guard on task_type mutations; add HTTP-layer test for locked-entry rejection.

---

## 2026-06-25

**What we worked on:** Task 10 — deployment & project docs (final build).

All 9 code tasks now complete. The app is fully working with:
- Timer-driven time tracking against projects (start/stop, manual entries)
- Per-project budget tracking and remaining budget display
- Invoicing: build per-project, group by task type, apply adjustments, lock/void, record history
- Overview landing page with budget bars and uninvoiced totals
- Settings for global rate and task type definitions
- 43 tests, all passing

Created final operational files:
- `deploy/mytime.service` — systemd unit for Debian deployment
- `README.md` — usage, deployment, architecture, data model, project layout
- Updated `WORKLOG.md` with this entry
- Updated `BACKLOG.md` with deferred items for future work

The app is ready for deployment to a LAN Debian server via the systemd unit.

---

## 2026-06-25

**What we worked on:** Task 4 — settings & task-type services + Settings page (TDD).

- Created `mytime/services/__init__.py` and `mytime/routers/__init__.py` (empty package inits).
- Implemented `settings_service.py`: `get_settings()` creates a default row idempotently; `update_settings()` mutates and commits.
- Implemented `task_types.py`: `list_task_types()` (ordered by `sort_order`, then `name`; `include_inactive` flag), `add_task_type()`, `rename_task_type()`, `set_active()`.
- Created `mytime/routers/settings.py` with GET /settings, POST /settings, and task-type CRUD endpoints (rename, toggle active). All POST routes redirect 303 to /settings.
- Created `mytime/templates/settings.html` extending `base.html`.
- Wired router into `main.py` via `app.include_router(settings_router.router)`.
- Wrote tests first (failing), then implemented (TDD as specified): `test_settings_service.py` (2 tests), `test_task_types.py` (3 tests), `test_settings_routes.py` (2 smoke tests).
- All 13 tests pass. Commit: `689899e feat: settings + task-type services and Settings page`.
- Pre-existing `on_event` deprecation warning in `main.py` noted — out of scope for this task.

## 2026-06-25

**What we worked on:** Tasks 1–3 — project scaffold, helpers, models/DB.

- Task 1: Initialised project with `uv`, FastAPI scaffold, base Jinja2 template, vendored HTMX, smoke test.
- Task 2: `clock.py` (wraps datetime for testability), `format.py` (hm/hms/money formatters), Jinja2 filter registration in `templating.py`.
- Task 3: Full SQLAlchemy model set (`Settings`, `TaskType`, `Project`, `TimeEntry`, `Invoice`, `InvoiceLine`) in `models.py`; `db.py` with engine, `SessionLocal`, `get_session()`, `init_db()`; `conftest.py` with `session` and `client` fixtures using in-memory SQLite.
