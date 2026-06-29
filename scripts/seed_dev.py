#!/usr/bin/env python3
"""
Populate dev.db with ~6 months of realistic dummy data.

Run from the project root:
    uv run python scripts/seed_dev.py

The script creates (or recreates) dev.db in the project root.
Start the dev server after seeding:
    MYTIME_DB_URL=sqlite:///dev.db uv run uvicorn mytime.main:app --reload
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

db_path = ROOT / "dev.db"
os.environ["MYTIME_DB_URL"] = f"sqlite:///{db_path}"

if db_path.exists():
    db_path.unlink()
    print(f"Removed existing {db_path.name}")

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from mytime.db import init_db, SessionLocal
from mytime.models import Client, Invoice, InvoiceLine, Project, Settings, TaskType, TimeEntry

init_db()
session = SessionLocal()


def dt(d: date, hour: int = 12) -> datetime:
    return datetime(d.year, d.month, d.day, hour, 0, 0)


def h(hours: float) -> int:
    return round(hours * 3600)


def q(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ── Settings ──────────────────────────────────────────────────────────────────
session.add(Settings(
    default_hourly_rate=Decimal("150"),
    currency_symbol="$",
    invoice_prefix="INV-",
    default_gst_rate=Decimal("15"),
))
session.flush()

# ── Task types ────────────────────────────────────────────────────────────────
tt = {}
for i, name in enumerate(["Development", "Research", "Meetings", "Documentation", "Project Mgmt"], 1):
    obj = TaskType(name=name, active=True, sort_order=i)
    session.add(obj)
    session.flush()
    tt[name] = obj

# ── Clients ───────────────────────────────────────────────────────────────────
cl = {}
for name, d in [
    ("Acme Corp",            date(2026, 1, 6)),
    ("Bright Ideas Ltd",     date(2026, 2, 3)),
    ("DataStream Analytics", date(2026, 1, 20)),
]:
    obj = Client(name=name, created_at=dt(d))
    session.add(obj)
    session.flush()
    cl[name] = obj

# ── Projects ──────────────────────────────────────────────────────────────────
# (client, name, rate, budget, status, created, gst_enabled, gst_rate)
project_specs = [
    ("Acme Corp",            "Website Redesign",  150, 20000, "active",   date(2026, 1,  6), True,  15),
    ("Acme Corp",            "SEO Consulting",    120,  None, "archived", date(2026, 2,  3), False, None),
    ("Bright Ideas Ltd",     "API Integration",   160, 15000, "active",   date(2026, 2,  3), False, None),
    ("Bright Ideas Ltd",     "Brand Strategy",    200,  None, "active",   date(2026, 4,  1), False, None),
    ("DataStream Analytics", "Data Pipeline",     175, 25000, "active",   date(2026, 1, 20), True,  15),
    ("DataStream Analytics", "Legacy Migration",  150, 10000, "archived", date(2026, 2, 10), False, None),
]

pr = {}
for client_name, name, rate, budget, status, created, gst_enabled, gst_rate in project_specs:
    obj = Project(
        client_name=client_name,
        name=name,
        hourly_rate=Decimal(str(rate)),
        budget=Decimal(str(budget)) if budget else None,
        status=status,
        created_at=dt(created),
        client_id=cl[client_name].id,
        gst_enabled=gst_enabled,
        gst_rate=Decimal(str(gst_rate)) if gst_rate else None,
    )
    session.add(obj)
    session.flush()
    pr[name] = obj

# ── Time entry helper ─────────────────────────────────────────────────────────
def e(project, task, d, hours, notes=None):
    entry = TimeEntry(
        project_id=project.id,
        task_type_id=tt[task].id,
        entry_date=d,
        seconds=h(hours),
        notes=notes,
        created_at=dt(d, hour=9),
    )
    session.add(entry)
    return entry


# ── Project 1: Acme Corp / Website Redesign ($150/hr, budget $20k, GST 15%) ──
# Phases 1 invoiced (INV-001, cutoff Mar 31); Phase 2 active/uninvoiced

p1_inv = [  # Jan–Mar — to be invoiced
    e(pr["Website Redesign"], "Development",  date(2026, 1,  7), 4.5, "Project setup, design system, component scaffold"),
    e(pr["Website Redesign"], "Meetings",     date(2026, 1,  8), 1.5, "Kickoff with Acme stakeholders"),
    e(pr["Website Redesign"], "Development",  date(2026, 1, 12), 5.0, "Homepage layout and navigation"),
    e(pr["Website Redesign"], "Development",  date(2026, 1, 14), 4.0, "About and services pages"),
    e(pr["Website Redesign"], "Meetings",     date(2026, 1, 16), 1.0, "Week 2 check-in"),
    e(pr["Website Redesign"], "Development",  date(2026, 1, 20), 4.5, "Blog listing and post template"),
    e(pr["Website Redesign"], "Documentation",date(2026, 1, 22), 2.0, "Design spec and component docs"),
    e(pr["Website Redesign"], "Development",  date(2026, 1, 26), 3.5, "Contact form and footer"),
    e(pr["Website Redesign"], "Development",  date(2026, 2,  2), 4.0, "Responsive layout and mobile nav"),
    e(pr["Website Redesign"], "Meetings",     date(2026, 2,  4), 1.0, "Design review with client"),
    e(pr["Website Redesign"], "Development",  date(2026, 2,  9), 5.0, "CMS integration and content types"),
    e(pr["Website Redesign"], "Development",  date(2026, 2, 11), 4.0, "Image optimisation and lazy loading"),
    e(pr["Website Redesign"], "Documentation",date(2026, 2, 13), 1.5, "CMS user guide"),
    e(pr["Website Redesign"], "Development",  date(2026, 2, 17), 4.5, "SEO metadata and structured data"),
    e(pr["Website Redesign"], "Meetings",     date(2026, 2, 18), 1.0, "Week 7 review"),
    e(pr["Website Redesign"], "Development",  date(2026, 2, 23), 3.5, "Performance optimisation"),
    e(pr["Website Redesign"], "Development",  date(2026, 2, 25), 3.0, "Cross-browser testing and fixes"),
    e(pr["Website Redesign"], "Documentation",date(2026, 2, 27), 1.5, "Testing checklist and handoff notes"),
    e(pr["Website Redesign"], "Development",  date(2026, 3,  2), 4.0, "Analytics integration and tracking"),
    e(pr["Website Redesign"], "Meetings",     date(2026, 3,  4), 1.5, "Pre-launch review meeting"),
    e(pr["Website Redesign"], "Development",  date(2026, 3,  9), 3.5, "UAT bug fixes"),
    e(pr["Website Redesign"], "Development",  date(2026, 3, 11), 3.0, "Final content entry and proofing"),
    e(pr["Website Redesign"], "Documentation",date(2026, 3, 13), 2.0, "Launch runbook"),
    e(pr["Website Redesign"], "Development",  date(2026, 3, 17), 4.0, "Deployment and DNS setup"),
    e(pr["Website Redesign"], "Meetings",     date(2026, 3, 18), 1.0, "Post-launch review call"),
    e(pr["Website Redesign"], "Development",  date(2026, 3, 23), 2.0, "Post-launch minor fixes"),
]
session.flush()
# Phase 1 total: ~76h × $150 = ~$11,400 + GST → INV-001

# Apr–Jun — uninvoiced (Phase 2: e-commerce)
e(pr["Website Redesign"], "Development",  date(2026, 4,  1), 3.0, "Phase 2 scoping and planning")
e(pr["Website Redesign"], "Meetings",     date(2026, 4,  3), 1.0, "Phase 2 kickoff call")
e(pr["Website Redesign"], "Development",  date(2026, 4,  8), 4.0, "E-commerce module foundation")
e(pr["Website Redesign"], "Development",  date(2026, 4, 10), 4.5, "Product catalogue and search")
e(pr["Website Redesign"], "Development",  date(2026, 4, 15), 3.5, "Shopping cart implementation")
e(pr["Website Redesign"], "Meetings",     date(2026, 4, 17), 1.0, "Phase 2 progress review")
e(pr["Website Redesign"], "Development",  date(2026, 5,  5), 4.0, "Checkout flow and payment integration")
e(pr["Website Redesign"], "Development",  date(2026, 5,  7), 3.5, "Order management backend")
e(pr["Website Redesign"], "Meetings",     date(2026, 5,  9), 1.0, "Weekly check-in")
e(pr["Website Redesign"], "Development",  date(2026, 5, 14), 3.0, "User account pages")
e(pr["Website Redesign"], "Development",  date(2026, 5, 20), 2.5, "Email notification templates")
e(pr["Website Redesign"], "Development",  date(2026, 6,  3), 4.0, "Integration testing and bug fixes")
e(pr["Website Redesign"], "Meetings",     date(2026, 6,  5), 1.0, "Client review session")
e(pr["Website Redesign"], "Development",  date(2026, 6, 10), 3.5, "Performance testing")
e(pr["Website Redesign"], "Documentation",date(2026, 6, 16), 2.0, "E-commerce technical docs")
e(pr["Website Redesign"], "Development",  date(2026, 6, 23), 3.0, "Pre-launch preparation")
session.flush()


# ── Project 2: Acme Corp / SEO Consulting ($120/hr, archived, fully invoiced) ─
p2_inv = [
    e(pr["SEO Consulting"], "Research",     date(2026, 2,  5), 2.5, "Keyword research and competitor analysis"),
    e(pr["SEO Consulting"], "Meetings",     date(2026, 2,  6), 1.0, "SEO strategy kickoff"),
    e(pr["SEO Consulting"], "Research",     date(2026, 2, 12), 3.0, "Technical SEO audit"),
    e(pr["SEO Consulting"], "Documentation",date(2026, 2, 19), 2.0, "SEO recommendations report"),
    e(pr["SEO Consulting"], "Research",     date(2026, 3,  5), 2.0, "Content gap analysis"),
    e(pr["SEO Consulting"], "Meetings",     date(2026, 3, 12), 1.0, "Progress update call"),
    e(pr["SEO Consulting"], "Research",     date(2026, 3, 19), 2.5, "Backlink analysis and strategy"),
    e(pr["SEO Consulting"], "Documentation",date(2026, 3, 26), 2.0, "Link building plan"),
    e(pr["SEO Consulting"], "Research",     date(2026, 4,  2), 2.0, "Implementation review and tracking setup"),
    e(pr["SEO Consulting"], "Meetings",     date(2026, 4,  9), 1.0, "Final review and handoff call"),
    e(pr["SEO Consulting"], "Documentation",date(2026, 4, 16), 2.0, "Final SEO report"),
]
session.flush()
# Total: ~21h × $120 = ~$2,520 → INV-003


# ── Project 3: Bright Ideas Ltd / API Integration ($160/hr, budget $15k) ─────
p3_inv = [  # Feb–Mar — to be invoiced
    e(pr["API Integration"], "Development",  date(2026, 2,  4), 4.0, "API architecture and auth setup"),
    e(pr["API Integration"], "Meetings",     date(2026, 2,  6), 1.0, "API requirements workshop"),
    e(pr["API Integration"], "Development",  date(2026, 2, 11), 5.0, "Core endpoint implementation"),
    e(pr["API Integration"], "Development",  date(2026, 2, 18), 4.5, "Data transformation layer"),
    e(pr["API Integration"], "Development",  date(2026, 2, 25), 3.5, "Error handling and validation"),
    e(pr["API Integration"], "Project Mgmt", date(2026, 2, 27), 1.0, "Sprint planning and backlog"),
    e(pr["API Integration"], "Development",  date(2026, 3,  4), 4.0, "Webhook implementation"),
    e(pr["API Integration"], "Meetings",     date(2026, 3,  6), 1.0, "Technical review with client"),
    e(pr["API Integration"], "Development",  date(2026, 3, 11), 5.0, "Rate limiting and caching layer"),
    e(pr["API Integration"], "Development",  date(2026, 3, 18), 4.0, "API documentation generation"),
    e(pr["API Integration"], "Development",  date(2026, 3, 25), 3.5, "Integration tests"),
    e(pr["API Integration"], "Project Mgmt", date(2026, 3, 28), 1.0, "Sprint review and progress report"),
]
session.flush()
# Total: ~37.5h × $160 = ~$6,000 → INV-005

# Apr–Jun — uninvoiced (SDK work)
e(pr["API Integration"], "Development",  date(2026, 4,  1), 4.5, "SDK client library foundation")
e(pr["API Integration"], "Meetings",     date(2026, 4,  3), 1.0, "Sprint review")
e(pr["API Integration"], "Development",  date(2026, 4,  8), 4.0, "Python SDK implementation")
e(pr["API Integration"], "Development",  date(2026, 4, 15), 4.5, "JavaScript SDK implementation")
e(pr["API Integration"], "Development",  date(2026, 4, 22), 3.5, "SDK testing and examples")
e(pr["API Integration"], "Project Mgmt", date(2026, 4, 25), 1.5, "v1.0 release planning")
e(pr["API Integration"], "Meetings",     date(2026, 4, 29), 1.0, "Client SDK demo")
e(pr["API Integration"], "Development",  date(2026, 5,  6), 4.0, "Versioning and changelog setup")
e(pr["API Integration"], "Development",  date(2026, 5, 13), 3.5, "Performance benchmarking")
e(pr["API Integration"], "Development",  date(2026, 5, 20), 4.0, "Security audit fixes")
e(pr["API Integration"], "Project Mgmt", date(2026, 5, 27), 1.5, "v1.0 release coordination")
e(pr["API Integration"], "Development",  date(2026, 6,  3), 3.0, "Post-release monitoring and fixes")
e(pr["API Integration"], "Meetings",     date(2026, 6,  5), 1.0, "Retrospective")
e(pr["API Integration"], "Development",  date(2026, 6, 10), 4.0, "v1.1 feature development")
e(pr["API Integration"], "Development",  date(2026, 6, 17), 3.5, "Additional endpoint development")
e(pr["API Integration"], "Development",  date(2026, 6, 24), 3.0, "Code review and quality pass")
session.flush()


# ── Project 4: Bright Ideas Ltd / Brand Strategy ($200/hr, no budget) ─────────
# Apr–Jun, fully uninvoiced
e(pr["Brand Strategy"], "Meetings",     date(2026, 4,  2), 2.0, "Brand discovery workshop part 1")
e(pr["Brand Strategy"], "Meetings",     date(2026, 4,  9), 2.0, "Brand discovery workshop part 2")
e(pr["Brand Strategy"], "Research",     date(2026, 4, 14), 3.0, "Competitor brand analysis")
e(pr["Brand Strategy"], "Documentation",date(2026, 4, 23), 4.0, "Brand positioning document draft")
e(pr["Brand Strategy"], "Meetings",     date(2026, 5,  7), 1.5, "Brand presentation to leadership")
e(pr["Brand Strategy"], "Research",     date(2026, 5, 14), 2.5, "Customer perception research")
e(pr["Brand Strategy"], "Documentation",date(2026, 5, 21), 3.0, "Brand guidelines draft v1")
e(pr["Brand Strategy"], "Meetings",     date(2026, 5, 28), 1.5, "Feedback review session")
e(pr["Brand Strategy"], "Documentation",date(2026, 6,  4), 3.5, "Brand guidelines v2 incorporating feedback")
e(pr["Brand Strategy"], "Meetings",     date(2026, 6, 11), 1.5, "Final brand presentation")
e(pr["Brand Strategy"], "Documentation",date(2026, 6, 18), 2.5, "Final brand guidelines and asset kit")
session.flush()


# ── Project 5: DataStream Analytics / Data Pipeline ($175/hr, budget $25k, GST) ─
p5_inv = [  # Jan–Feb — to be invoiced
    e(pr["Data Pipeline"], "Development", date(2026, 1, 20), 4.0, "Pipeline architecture design"),
    e(pr["Data Pipeline"], "Research",    date(2026, 1, 21), 2.0, "Data source evaluation"),
    e(pr["Data Pipeline"], "Development", date(2026, 1, 26), 5.0, "Ingestion layer implementation"),
    e(pr["Data Pipeline"], "Development", date(2026, 1, 27), 4.0, "Data schema and validation"),
    e(pr["Data Pipeline"], "Development", date(2026, 1, 28), 4.5, "Transformation layer core"),
    e(pr["Data Pipeline"], "Meetings",    date(2026, 1, 29), 1.5, "Sprint review with DataStream team"),
    e(pr["Data Pipeline"], "Development", date(2026, 2,  2), 5.0, "ETL job scheduling"),
    e(pr["Data Pipeline"], "Development", date(2026, 2,  4), 4.0, "Error handling and retry logic"),
    e(pr["Data Pipeline"], "Research",    date(2026, 2,  5), 2.0, "Performance benchmarking research"),
    e(pr["Data Pipeline"], "Development", date(2026, 2,  9), 4.5, "Output layer and data sinks"),
    e(pr["Data Pipeline"], "Development", date(2026, 2, 11), 3.5, "Monitoring and alerting setup"),
    e(pr["Data Pipeline"], "Meetings",    date(2026, 2, 13), 1.5, "Architecture review"),
    e(pr["Data Pipeline"], "Development", date(2026, 2, 17), 4.0, "Testing framework for pipeline"),
    e(pr["Data Pipeline"], "Development", date(2026, 2, 19), 4.0, "Unit tests for all components"),
    e(pr["Data Pipeline"], "Research",    date(2026, 2, 23), 2.0, "Optimisation strategies research"),
    e(pr["Data Pipeline"], "Development", date(2026, 2, 25), 4.5, "Performance optimisation pass 1"),
    e(pr["Data Pipeline"], "Meetings",    date(2026, 2, 27), 1.5, "Month-end review"),
]
session.flush()
# Total: ~57.5h × $175 = ~$10,062.50 + GST → INV-002

# Mar–Jun — uninvoiced (will push project slightly over budget)
e(pr["Data Pipeline"], "Development", date(2026, 3,  2), 5.0, "Production deployment and cutover")
e(pr["Data Pipeline"], "Research",    date(2026, 3,  3), 2.0, "Production performance analysis")
e(pr["Data Pipeline"], "Development", date(2026, 3,  9), 4.5, "Real-time processing enhancements")
e(pr["Data Pipeline"], "Development", date(2026, 3, 11), 4.0, "Data quality validation rules")
e(pr["Data Pipeline"], "Meetings",    date(2026, 3, 13), 1.5, "Stakeholder update")
e(pr["Data Pipeline"], "Development", date(2026, 3, 17), 5.0, "Historical data backfill pipeline")
e(pr["Data Pipeline"], "Development", date(2026, 3, 19), 4.0, "Dashboard and reporting layer")
e(pr["Data Pipeline"], "Research",    date(2026, 3, 24), 2.0, "ML feature engineering research")
e(pr["Data Pipeline"], "Development", date(2026, 4,  7), 4.5, "ML feature pipeline foundation")
e(pr["Data Pipeline"], "Development", date(2026, 4,  9), 4.0, "Feature store implementation")
e(pr["Data Pipeline"], "Meetings",    date(2026, 4, 14), 1.5, "Sprint planning")
e(pr["Data Pipeline"], "Development", date(2026, 4, 16), 4.5, "Real-time feature computation")
e(pr["Data Pipeline"], "Research",    date(2026, 4, 22), 2.0, "Stream processing evaluation")
e(pr["Data Pipeline"], "Development", date(2026, 4, 24), 4.0, "Stream processing integration")
e(pr["Data Pipeline"], "Development", date(2026, 5,  5), 4.0, "Kafka integration layer")
e(pr["Data Pipeline"], "Development", date(2026, 5,  7), 3.5, "Consumer group management")
e(pr["Data Pipeline"], "Research",    date(2026, 5, 12), 2.0, "Throughput scaling research")
e(pr["Data Pipeline"], "Meetings",    date(2026, 5, 14), 1.5, "Performance review with team")
e(pr["Data Pipeline"], "Development", date(2026, 5, 20), 4.0, "Horizontal scaling implementation")
e(pr["Data Pipeline"], "Development", date(2026, 5, 26), 3.5, "Observability and tracing")
e(pr["Data Pipeline"], "Development", date(2026, 6,  2), 4.5, "SLA monitoring and alerting")
e(pr["Data Pipeline"], "Development", date(2026, 6,  9), 4.0, "Auto-scaling configuration")
e(pr["Data Pipeline"], "Research",    date(2026, 6, 11), 2.0, "Cost optimisation analysis")
e(pr["Data Pipeline"], "Meetings",    date(2026, 6, 16), 1.5, "Quarterly review")
e(pr["Data Pipeline"], "Development", date(2026, 6, 23), 4.0, "Cost optimisation implementation")
e(pr["Data Pipeline"], "Development", date(2026, 6, 25), 3.5, "Pipeline hardening and reliability fixes")
e(pr["Data Pipeline"], "Meetings",    date(2026, 6, 26), 1.0, "Month-end status update")
session.flush()
# Mar–Jun adds ~88h → grand total ~145.5h × $175 = ~$25,462.50 — slightly over $25k budget


# ── Project 6: DataStream / Legacy Migration ($150/hr, budget $10k, archived) ─
p6_inv = [
    e(pr["Legacy Migration"], "Development",  date(2026, 2, 10), 4.5, "Legacy codebase analysis"),
    e(pr["Legacy Migration"], "Research",     date(2026, 2, 12), 2.5, "Migration strategy research"),
    e(pr["Legacy Migration"], "Development",  date(2026, 2, 17), 5.0, "Data extraction and mapping"),
    e(pr["Legacy Migration"], "Documentation",date(2026, 2, 19), 2.0, "Migration plan documentation"),
    e(pr["Legacy Migration"], "Development",  date(2026, 2, 24), 4.0, "Schema transformation scripts"),
    e(pr["Legacy Migration"], "Development",  date(2026, 3,  3), 5.0, "ETL migration pipeline"),
    e(pr["Legacy Migration"], "Development",  date(2026, 3, 10), 4.5, "Data validation and reconciliation"),
    e(pr["Legacy Migration"], "Project Mgmt", date(2026, 3, 12), 1.5, "Mid-project review"),
    e(pr["Legacy Migration"], "Development",  date(2026, 3, 17), 4.0, "Cutover scripts and rollback plan"),
    e(pr["Legacy Migration"], "Documentation",date(2026, 3, 24), 2.0, "Post-migration runbook"),
    e(pr["Legacy Migration"], "Development",  date(2026, 4,  7), 4.0, "Staging environment migration"),
    e(pr["Legacy Migration"], "Development",  date(2026, 4,  9), 3.5, "Data quality verification"),
    e(pr["Legacy Migration"], "Project Mgmt", date(2026, 4, 14), 1.5, "Pre-production sign-off"),
    e(pr["Legacy Migration"], "Development",  date(2026, 4, 21), 4.0, "Production cutover"),
    e(pr["Legacy Migration"], "Documentation",date(2026, 4, 23), 2.0, "Lessons learned document"),
    e(pr["Legacy Migration"], "Project Mgmt", date(2026, 4, 28), 1.0, "Project closeout"),
]
session.flush()
# Total: ~51h × $150 = ~$7,650 (under $10k budget) → INV-004


# ── Invoices ──────────────────────────────────────────────────────────────────
def create_invoice(project, number, cutoff, entries, created):
    rate = project.hourly_rate
    tracked: dict[int, int] = {}
    for entry in entries:
        tracked[entry.task_type_id] = tracked.get(entry.task_type_id, 0) + entry.seconds

    total = Decimal("0.00")
    lines = []
    for tid, secs in tracked.items():
        amount = q(Decimal(secs) / 3600 * rate)
        total += amount
        lines.append((tid, secs, amount))

    gst_amount = None
    if project.gst_enabled and project.gst_rate:
        gst_amount = q(total * project.gst_rate / Decimal("100"))

    inv = Invoice(
        project_id=project.id,
        created_at=dt(created, hour=10),
        cutoff_date=cutoff,
        rate_snapshot=rate,
        total_amount=q(total),
        invoice_number=number,
        gst_amount=gst_amount,
    )
    session.add(inv)
    session.flush()

    for tid, secs, amount in lines:
        session.add(InvoiceLine(
            invoice_id=inv.id,
            task_type_id=tid,
            tracked_seconds=secs,
            invoiced_seconds=secs,
            amount=amount,
        ))

    for entry in entries:
        entry.invoice_id = inv.id

    session.flush()
    return inv


create_invoice(pr["Website Redesign"], "INV-001", date(2026, 3, 31), p1_inv, date(2026, 4, 2))
create_invoice(pr["Data Pipeline"],    "INV-002", date(2026, 2, 28), p5_inv, date(2026, 3, 2))
create_invoice(pr["SEO Consulting"],   "INV-003", date(2026, 4, 30), p2_inv, date(2026, 5, 2))
create_invoice(pr["Legacy Migration"], "INV-004", date(2026, 4, 30), p6_inv, date(2026, 5, 2))
create_invoice(pr["API Integration"],  "INV-005", date(2026, 3, 31), p3_inv, date(2026, 4, 2))

session.commit()
session.close()

print("dev.db seeded successfully.")
print()
print("Start the dev server:")
print("  MYTIME_DB_URL=sqlite:///dev.db uv run uvicorn mytime.main:app --reload --port 8001")
print()
print("Then visit: http://localhost:8001/today")
