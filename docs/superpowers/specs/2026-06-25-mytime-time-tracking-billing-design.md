# mytime — Time Tracking & Billing App — Design

**Date:** 2026-06-25
**Status:** Approved design, ready for implementation planning

## 1. Purpose & scope

A single-user web app for a solo consulting business to track time and manage
billing. Runs on a Debian server on the local network only — **not externally
accessible**. No authentication or user management at this stage.

Three core functions: **Projects**, **Time tracking**, **Invoicing**, plus a
**Project overview** landing page. Typical load: 3–6 active projects at a time.

The app does **not** generate invoice documents. It tracks which time has been
invoiced and tells the user how much time to invoice, broken down by task type.

## 2. Architecture

- **Backend:** FastAPI (Python), server-rendered HTML via Jinja2 templates.
- **Interactivity:** HTMX for in-place edits, modal/inline forms, and the live
  invoice builder — minimal hand-written JavaScript.
- **Storage:** SQLite via SQLAlchemy.
- **Serving:** single Uvicorn process, deployed as a **systemd service** on the
  Debian box, bound to the LAN. No auth.
- **Charts:** the overview bars are rendered server-side as inline HTML/CSS — no
  charting dependency.

### App structure (layered-lite)

```
mytime/
  main.py            # FastAPI app, startup (create_all), nav
  db.py              # engine + session
  models.py          # SQLAlchemy tables
  routers/
    overview.py
    projects.py
    time_entries.py
    invoices.py
    settings.py
  services/          # pure, testable logic (no web plumbing)
    budget.py        # invoiced/uninvoiced value, remaining/exceedance
    invoicing.py     # group uninvoiced by task, apply adjustments, lock
    guards.py        # delete-project / void-invoice rules
  templates/         # Jinja2 + HTMX partials
  static/            # CSS + htmx lib
  tests/
```

The genuinely tricky logic (invoicing rules, budget math, integrity guards)
lives in `services/` as pure functions, isolated from the web layer so it can be
unit-tested directly.

## 3. Data model

Durations are stored as **integer minutes** throughout (hours & minutes are only
an input/display format). Money is decimal dollars.

### `settings` (single row)
- `default_hourly_rate` — pre-fills new projects' rate
- `currency_symbol` — default `$`

### `task_type`
- `id`, `name`, `active` (bool), `sort_order` (optional)
- Global list, shared across all projects, managed in Settings.
- Tasks are **retired** (`active = false`), never hard-deleted, so historical
  entries and invoice lines keep their labels.

### `project`
- `id`, `client_name`, `name`
- `budget` (nullable, dollars)
- `description` (nullable)
- `hourly_rate` (dollars; pre-filled from `settings.default_hourly_rate` on
  create, editable, may be `0` for internal projects)
- `status` (`active` | `archived`)
- `created_at`

### `time_entry`
- `id`, `project_id`, `task_type_id`
- `notes` (nullable)
- `entry_date`
- `minutes` (int)
- `invoice_id` (nullable FK)
- `created_at`
- An entry is **invoiced/locked exactly when `invoice_id` is set**. Locked
  entries reject edit and delete at the service layer.

### `invoice`
- `id`, `project_id`
- `created_at` (invoice date)
- `cutoff_date` (the "up to" date used when building the invoice)
- `rate_snapshot` (project rate captured at invoicing time)
- `total_amount` (dollars)

### `invoice_line` (one per task type on an invoice)
- `id`, `invoice_id`, `task_type_id`
- `tracked_minutes` (sum of included entries for that task type)
- `invoiced_minutes` (the adjusted figure entered by the user)
- `amount` (= `invoiced_minutes / 60 × rate_snapshot`)

### Derived figures
- **Invoiced value** (project) = Σ `invoice.total_amount`
- **Uninvoiced value** = (Σ uninvoiced `minutes` / 60) × **current** project rate
- **Total tracked time** = Σ all `minutes` for the project (invoiced + uninvoiced)
- **Budget remaining** = `budget − (invoiced value + uninvoiced value)`;
  negative ⇒ exceedance

## 4. Invoicing

Invoicing is always **per-project**, on **uninvoiced** time, broken down **by
task type**. Adjustments (rounding, budget caps) are made **per task type**.

### Building an invoice
1. From the project page, **New invoice**. Pick a **cutoff date** (defaults to
   today).
2. Gather all uninvoiced entries for that project with `entry_date ≤ cutoff`,
   group **by task type**, and show a builder table: one row per task type with
   **tracked** (read-only, e.g. `5h 42m`) and an editable **invoiced** field
   (pre-filled = tracked, so the default invoice equals tracked time).
3. The user adjusts each row — round up/down, cap for budget, or set `0` to write
   a task off. A running **total $** (and budget-remaining preview) updates live
   via HTMX using the project's current rate.
4. **Save** → creates the `invoice` (snapshotting the rate), writes one
   `invoice_line` per task type, and stamps every included entry with
   `invoice_id` (locking them).

### Leftover time
When invoiced minutes < tracked minutes, the difference is **written off**: all
included entries are locked regardless, and the lower invoiced figure is simply
recorded. Leftover time does **not** reappear on future invoices.

### Invoice list / view
Each project lists its past invoices (date, cutoff, total, per-task lines). An
invoice can be **voided**: this unlocks its entries (clears `invoice_id`) and
deletes the invoice + lines (with confirmation), allowing correction of mistakes.

## 5. Project overview

The landing page (`/`) shows a card per **active** project:

- Client name, project name, current hourly rate.
- **Total tracked time** (`Xh Ym`, invoiced + uninvoiced).
- Quick numbers: invoiced $, uninvoiced $, budget remaining / exceeded.
- A **horizontal stacked bar in dollars**, inline HTML/CSS:
  - Segment 1 — **Invoiced value**
  - Segment 2 — **Uninvoiced value**
  - Segment 3 — **Remaining budget** (only if the project has a budget)
  - If over budget, the bar fills to the budget line and an **exceedance** amount
    is shown in a contrasting colour past the line.
  - Projects **without** a budget show only the invoiced + uninvoiced segments
    with dollar labels (no remaining/exceedance).

## 6. Pages & navigation

Top nav: **Overview · Projects · Time · Settings**.

- **Overview** (`/`) — project cards (active projects only).
- **Projects** (`/projects`) — table with an **Active / Archived** filter toggle.
  Row actions: Edit, Archive/Unarchive, Delete (guarded), and link to detail.
  - **Project detail** (`/projects/{id}`) — attributes + budget bar; sections for
    **Time entries** (this project) and **Invoices**; buttons for **New time
    entry** and **New invoice**.
- **Time** (`/time`) — global time-entry list across all projects, newest first,
  with filters (project, date range). Add/Edit/Delete. Add-entry form: project,
  task type, date, hours + minutes, notes. Locked (invoiced) entries shown greyed
  with no edit/delete.
- **Settings** (`/settings`) — default hourly rate, currency symbol, and task
  type management (add, rename, retire/reactivate).

Forms and inline actions use HTMX (modal or inline partials) so edits happen
without full page reloads. Light custom CSS, no front-end framework.

## 7. Actions reference

**Projects:** add, edit, archive, unarchive, delete.
- *Delete* is permitted **only when the project has no invoices** (protects
  billing history); if invoices exist the UI steers to *Archive*. Deleting an
  invoice-free project also removes its time entries.

**Time entries:** add, edit, delete.
- Edit/delete blocked once the entry is invoiced (locked).

**Invoices:** create, view, void.
- *Void* unlocks included entries and removes the invoice + lines.

## 8. Testing

- **pytest** over the isolated service functions:
  - budget math (invoiced/uninvoiced value, remaining/exceedance, no-budget case)
  - invoice building (grouping by task, adjustment, rate snapshot, locking)
  - integrity guards (delete-project, void-invoice, locked-entry edit/delete)
- A few HTTP smoke tests via FastAPI `TestClient` for the main routes.

## 9. Out of scope (this stage)

- Authentication / user management / multi-user.
- External accessibility and related security hardening.
- Invoice document generation (PDF/printing) — done separately by the user.
- Per-project task lists (global list only).
- Carrying forward leftover/uninvoiced-over-budget time (written off instead).
