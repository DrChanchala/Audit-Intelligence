"""Database access: one small, dialect-aware layer over SQLite and PostgreSQL.

* SQL is written once with ``?`` placeholders; they are translated to ``%s``
  for psycopg2 by a tokenizer that ignores string literals (the old
  ``str.replace('?', '%s')`` corrupted any literal containing ``?`` or ``%``).
* PostgreSQL connections come from a thread-safe pool (FastAPI runs sync
  endpoints in a threadpool).
* ``Session`` is a unit of work: commit on success, rollback on any error.
"""
from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from app.core.config import get_settings


class Row(dict):
    """Dict row that also supports positional access (row[0], row[:2])."""

    def __init__(self, keys: Sequence[str], values: Sequence[Any]):
        super().__init__(zip(keys, values))
        self._values = tuple(values)

    def __getitem__(self, key):  # type: ignore[override]
        if isinstance(key, (int, slice)):
            return self._values[key]
        return super().__getitem__(key)


def to_pg_sql(sql: str) -> str:
    """Translate ``?`` -> ``%s``, keep '?' and '%' inside string literals, and escape '%' outside literals."""
    out: list[str] = []
    quote: str | None = None
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if quote:
            out.append(ch)
            if ch == "\\" and i + 1 < n:
                i += 1
                out.append(sql[i])
            elif ch == quote:
                if i + 1 < n and sql[i + 1] == quote:
                    i += 1
                    out.append(sql[i])
                else:
                    quote = None
        else:
            if ch in ("'", '"'):
                quote = ch
                out.append(ch)
            elif ch == "?":
                out.append("%s")
            elif ch == "%":
                out.append("%%")
            else:
                out.append(ch)
        i += 1
    return "".join(out)


def _normalise(value: Any) -> Any:
    # psycopg2 returns date/datetime/Decimal; the API contract has always been strings/numbers.
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if type(value).__name__ == "Decimal":
        return float(value)
    return value


class Session:
    def __init__(self, conn: Any, dialect: str):
        self._conn = conn
        self.dialect = dialect

    def _cursor(self, sql: str, params: Sequence[Any] | None):
        cur = self._conn.cursor()
        if self.dialect == "postgres":
            cur.execute(to_pg_sql(sql), tuple(params or ()))
        else:
            cur.execute(sql, tuple(params or ()))
        return cur

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> int:
        cur = self._cursor(sql, params)
        count = cur.rowcount
        cur.close()
        return count

    def executemany(self, sql: str, rows: Sequence[Sequence[Any]]) -> None:
        cur = self._conn.cursor()
        cur.executemany(to_pg_sql(sql) if self.dialect == "postgres" else sql, [tuple(r) for r in rows])
        cur.close()

    def all(self, sql: str, params: Sequence[Any] | None = None) -> list[Row]:
        cur = self._cursor(sql, params)
        keys = [d[0] for d in cur.description or []]
        rows = [Row(keys, [_normalise(v) for v in r]) for r in cur.fetchall()]
        cur.close()
        return rows

    def one(self, sql: str, params: Sequence[Any] | None = None) -> Row | None:
        rows = self.all(sql, params)
        return rows[0] if rows else None

    def scalar(self, sql: str, params: Sequence[Any] | None = None) -> Any:
        row = self.one(sql, params)
        return row[0] if row else None

    def in_clause(self, values: Sequence[Any]) -> str:
        return ",".join("?" for _ in values) or "NULL"

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()


class Database:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.dialect = "postgres" if self.settings.uses_postgres else "sqlite"
        self._pool = None
        self._lock = threading.Lock()

    def _pg_pool(self):
        if self._pool is None:
            with self._lock:
                if self._pool is None:
                    from psycopg2.pool import ThreadedConnectionPool

                    url = self.settings.database_url or ""
                    if url.startswith("postgres://"):
                        url = url.replace("postgres://", "postgresql://", 1)
                    self._pool = ThreadedConnectionPool(1, 10, dsn=url, connect_timeout=10)
        return self._pool

    @contextmanager
    def session(self) -> Iterator[Session]:
        if self.dialect == "postgres":
            pool = self._pg_pool()
            conn = pool.getconn()
            try:
                s = Session(conn, "postgres")
                yield s
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                pool.putconn(conn)
        else:
            path = self.settings.sqlite_path
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path, timeout=15, check_same_thread=False)
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            try:
                s = Session(conn, "sqlite")
                yield s
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def close(self) -> None:
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None


_db: Database | None = None


def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


def reset_database() -> None:
    """Used by tests after changing settings."""
    global _db
    if _db is not None:
        _db.close()
    _db = None


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one transaction per request."""
    with get_database().session() as s:
        yield s
