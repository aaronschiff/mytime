#!/usr/bin/env python3
"""mytime daily database backup with verification, tiered retention, and
optional off-site push.

Unlike a plain file copy, this takes a transactionally consistent snapshot via
SQLite's online backup API (safe to run while the app is writing), then verifies
the result before keeping it. A backup that fails verification is deleted and the
script exits non-zero so the failure is loud (systemd marks the unit failed)
rather than silently leaving a corrupt file.

Retention policy:
  - Last 28 days: keep each daily snapshot
  - Older: keep one snapshot per 28-day period (the newest in each period)

Configure via environment variables:
  MYTIME_DB_PATH      — path to the live mytime.db
                        (default: /opt/mytime/mytime.db)
  MYTIME_BACKUP_DIR   — directory for backup files
                        (default: /var/backups/mytime)
  MYTIME_OFFSITE_DEST — optional rsync destination for an off-site copy,
                        e.g. "user@vps:/srv/mytime-backups". If unset, no
                        off-site push is attempted.
"""
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(os.environ.get("MYTIME_DB_PATH", "/opt/mytime/mytime.db"))
BACKUP_DIR = Path(os.environ.get("MYTIME_BACKUP_DIR", "/var/backups/mytime"))
OFFSITE_DEST = os.environ.get("MYTIME_OFFSITE_DEST")
_PATTERN = re.compile(r"^mytime-(\d{4}-\d{2}-\d{2})\.db$")


class BackupVerificationError(Exception):
    """Raised when a backup file is not a valid, usable mytime database."""


def make_backup(src: Path, dest: Path) -> None:
    """Write a transactionally consistent snapshot of ``src`` to ``dest``.

    Uses SQLite's online backup API, which is safe to run concurrently with the
    live app: the snapshot reflects the last committed state and never captures
    a torn file or an in-flight transaction.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(f"file:{src}?mode=ro", uri=True)
    try:
        target = sqlite3.connect(dest)
        try:
            with target:
                source.backup(target)
        finally:
            target.close()
    finally:
        source.close()


def verify_backup(path: Path) -> None:
    """Raise ``BackupVerificationError`` unless ``path`` is a usable backup.

    Checks that the file is a valid SQLite database (``PRAGMA integrity_check``)
    and that the expected schema is present and queryable.
    """
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise BackupVerificationError(f"integrity_check: {result}")
            conn.execute("SELECT count(*) FROM time_entry").fetchone()
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise BackupVerificationError(str(exc)) from exc


def offsite_command(backup_dir: Path, dest: str) -> list[str]:
    """Build the rsync argv that mirrors ``backup_dir`` to an off-site ``dest``.

    No ``--delete``: the off-site copy accumulates history independently of local
    pruning, so it remains a complete second line of defence.
    """
    return ["rsync", "-az", "-e", "ssh", f"{backup_dir}/", dest]


def push_offsite(backup_dir: Path, dest: str) -> None:
    """Mirror local backups off-site. Raises on rsync failure."""
    subprocess.run(offsite_command(backup_dir, dest), check=True)


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

    make_backup(DB_PATH, dest)
    try:
        verify_backup(dest)
    except BackupVerificationError as exc:
        dest.unlink(missing_ok=True)
        print(f"ERROR: backup verification failed, discarded {dest.name}: {exc}",
              file=sys.stderr)
        sys.exit(1)
    print(f"Backed up and verified: {dest}")

    _prune(today, _load_backups())

    if OFFSITE_DEST:
        try:
            push_offsite(BACKUP_DIR, OFFSITE_DEST)
            print(f"Pushed off-site to: {OFFSITE_DEST}")
        except (subprocess.CalledProcessError, OSError) as exc:
            # The local verified backup already succeeded; an off-site failure
            # should be loud but must not discard the good local copy.
            print(f"ERROR: off-site push to {OFFSITE_DEST} failed: {exc}",
                  file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    main()
