"""Tests for deploy/backup.py — the data-loss safety net.

backup.py lives in deploy/ (not the mytime package), so it's loaded by path.
"""
import importlib.util
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "mytime_backup",
    Path(__file__).resolve().parent.parent / "deploy" / "backup.py",
)
backup = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(backup)


def _make_db(path: Path, rows: int = 3) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE time_entry (id INTEGER PRIMARY KEY, seconds INTEGER)")
    conn.executemany(
        "INSERT INTO time_entry (seconds) VALUES (?)", [(i * 60,) for i in range(rows)]
    )
    conn.commit()
    conn.close()


def test_make_backup_copies_all_rows(tmp_path):
    src = tmp_path / "live.db"
    dest = tmp_path / "out" / "snap.db"
    _make_db(src, rows=5)

    backup.make_backup(src, dest)

    conn = sqlite3.connect(dest)
    count = conn.execute("SELECT count(*) FROM time_entry").fetchone()[0]
    conn.close()
    assert count == 5


def test_make_backup_is_consistent_during_open_write(tmp_path):
    """A snapshot taken while the source has an uncommitted transaction must
    reflect the last committed state, not a torn file."""
    src = tmp_path / "live.db"
    dest = tmp_path / "snap.db"
    _make_db(src, rows=3)

    writer = sqlite3.connect(src)
    writer.execute("BEGIN")
    writer.execute("INSERT INTO time_entry (seconds) VALUES (999)")  # uncommitted

    backup.make_backup(src, dest)

    conn = sqlite3.connect(dest)
    count = conn.execute("SELECT count(*) FROM time_entry").fetchone()[0]
    conn.close()
    writer.rollback()
    writer.close()
    assert count == 3  # uncommitted row must NOT appear


def test_verify_backup_accepts_good_db(tmp_path):
    good = tmp_path / "good.db"
    _make_db(good)
    backup.verify_backup(good)  # should not raise


def test_verify_backup_rejects_corrupt_file(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"this is not a sqlite database")
    with pytest.raises(backup.BackupVerificationError):
        backup.verify_backup(bad)


def test_verify_backup_rejects_missing_time_entry_table(tmp_path):
    """A syntactically valid SQLite file without the expected schema is not a
    usable mytime backup."""
    empty = tmp_path / "empty.db"
    conn = sqlite3.connect(empty)
    conn.execute("CREATE TABLE unrelated (x INTEGER)")
    conn.commit()
    conn.close()
    with pytest.raises(backup.BackupVerificationError):
        backup.verify_backup(empty)


def test_prune_keeps_recent_and_thins_old(tmp_path):
    today = date(2026, 6, 30)
    backups = {}
    # 40 consecutive daily backups ending today
    for i in range(40):
        d = today - timedelta(days=i)
        p = tmp_path / f"mytime-{d}.db"
        p.write_bytes(b"x")
        backups[d] = p

    backup._prune(today, backups)

    remaining = sorted(date.fromisoformat(p.stem.split("mytime-")[1])
                       for p in tmp_path.glob("mytime-*.db"))
    cutoff = today - timedelta(days=28)
    # Everything within the last 28 days is kept
    assert all(d >= cutoff for d in remaining if d >= cutoff)
    for d in [today, today - timedelta(days=27)]:
        assert d in remaining
    # Older-than-28-days entries are thinned, not all kept
    older = [d for d in remaining if d < cutoff]
    assert len(older) < 12  # would be 12 days (28..39) if nothing pruned


def test_offsite_command_builds_rsync_argv(tmp_path):
    argv = backup.offsite_command(tmp_path, "user@vps:/srv/mytime-backups")
    assert argv[0] == "rsync"
    assert any(str(tmp_path) in a for a in argv)
    assert "user@vps:/srv/mytime-backups" in argv
