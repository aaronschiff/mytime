from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from mytime import clock


class Base(DeclarativeBase):
    pass


class Settings(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    default_hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    currency_symbol: Mapped[str] = mapped_column(String(8), default="$")


class TaskType(Base):
    __tablename__ = "task_type"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Project(Base):
    __tablename__ = "project"
    id: Mapped[int] = mapped_column(primary_key=True)
    client_name: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(200))
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hourly_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clock.now)


class TimeEntry(Base):
    __tablename__ = "time_entry"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    task_type_id: Mapped[int] = mapped_column(ForeignKey("task_type.id"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_date: Mapped[date] = mapped_column(Date)
    seconds: Mapped[int] = mapped_column(Integer, default=0)
    running_since: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoice.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clock.now)


class Invoice(Base):
    __tablename__ = "invoice"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=clock.now)
    cutoff_date: Mapped[date] = mapped_column(Date)
    rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))


class InvoiceLine(Base):
    __tablename__ = "invoice_line"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id"))
    task_type_id: Mapped[int] = mapped_column(ForeignKey("task_type.id"))
    tracked_seconds: Mapped[int] = mapped_column(Integer)
    invoiced_seconds: Mapped[int] = mapped_column(Integer)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
