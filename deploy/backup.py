#!/usr/bin/env python3
"""mytime daily database backup with tiered retention.

Retention policy:
  - Last 28 days: keep each daily snapshot
  - Older: keep one snapshot per 28-day period (the newest in each period)
"""
import re
import shutil
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path("/home/aaron/mytime/mytime.db")
BACKUP_DIR = Path("/data/mytime-backup")
_PATTERN = re.compile(r"^mytime-(\d{4}-\d{2}-\d{2})\.db$")


def _load_backups() -> dict[date, Path]:
    result = {}
    for path in BACKUP_DIR.glob("mytime-*.db"):
        m = _PATTERN.match(path.name)
        if m:
            result[date.fromisoformat(m.group(1))] = path
    return result


def _prune(today: date, backups: dict[date, Path]) -> None:
    cutoff = today - timedelta(days=28)

    # For each 28-day period older than cutoff, find the newest backup to keep.
    keep_per_period: dict[int, date] = {}
    for d in backups:
        if d >= cutoff:
            continue
        age = (today - d).days
        period = (age - 28) // 28  # 0 = days 28-55, 1 = days 56-83, etc.
        if period not in keep_per_period or d > keep_per_period[period]:
            keep_per_period[period] = d

    keep_dates = set(keep_per_period.values())
    for d, path in backups.items():
        if d < cutoff and d not in keep_dates:
            path.unlink()
            print(f"Pruned: {path.name}")


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    dest = BACKUP_DIR / f"mytime-{today}.db"
    shutil.copy2(DB_PATH, dest)
    print(f"Backed up to: {dest}")
    _prune(today, _load_backups())


if __name__ == "__main__":
    main()
