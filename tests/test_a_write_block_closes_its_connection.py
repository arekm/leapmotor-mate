"""`with _conn_rw() as db:` commits or rolls back like sqlite3's own context manager, and then closes,
which sqlite3's does not: the connection's statement cache keeps it in a reference cycle, so one left
open stays open until the cyclic collector runs."""
import sqlite3

import db as D
import db_reader
import pytest


def _is_closed(conn):
    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        return True
    return False


def test_a_write_block_commits_and_closes_on_the_way_out(tmp_path, monkeypatch):
    """Another connection sees the row, and the one the block used is closed."""
    D.Database(str(tmp_path / "t.db")).close()
    monkeypatch.setattr(db_reader, "DB_PATH", str(tmp_path / "t.db"))
    with db_reader._conn_rw() as db:
        db.execute("INSERT INTO settings (key, value) VALUES ('probe', '1')")
    assert _is_closed(db)
    other = sqlite3.connect(str(tmp_path / "t.db"))
    try:
        assert other.execute("SELECT value FROM settings WHERE key = 'probe'").fetchone() == ("1",)
    finally:
        other.close()


def test_a_write_block_that_raises_rolls_back_and_still_closes(tmp_path, monkeypatch):
    D.Database(str(tmp_path / "t.db")).close()
    monkeypatch.setattr(db_reader, "DB_PATH", str(tmp_path / "t.db"))
    with pytest.raises(RuntimeError), db_reader._conn_rw() as db:
        db.execute("INSERT INTO settings (key, value) VALUES ('probe', '1')")
        raise RuntimeError("boom")
    assert _is_closed(db)
    other = sqlite3.connect(str(tmp_path / "t.db"))
    try:
        assert other.execute("SELECT value FROM settings WHERE key = 'probe'").fetchone() is None
    finally:
        other.close()
