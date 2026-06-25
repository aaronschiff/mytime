# Worklog

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
