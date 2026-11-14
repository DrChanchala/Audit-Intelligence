"""Database and dialect translation tests (spec §8 item 9)."""
from __future__ import annotations

import sqlite3

import pytest

from app.db.connection import Row, Session, to_pg_sql
from app.db.schema import init_schema, load_master_checklist


class TestToPgSql:
    """Verify that to_pg_sql translates ? -> %s, keeps '?' and '%' inside literals, and escapes '%' outside."""

    def test_basic_placeholder(self):
        assert to_pg_sql("SELECT * FROM users WHERE id = ?") == "SELECT * FROM users WHERE id = %s"

    def test_multiple_placeholders(self):
        assert to_pg_sql("INSERT INTO t (a, b, c) VALUES (?, ?, ?)") == "INSERT INTO t (a, b, c) VALUES (%s, %s, %s)"

    def test_keeps_question_mark_inside_literal(self):
        sql = "SELECT 'Is this genuine?' AS question FROM items WHERE id = ?"
        expected = "SELECT 'Is this genuine?' AS question FROM items WHERE id = %s"
        assert to_pg_sql(sql) == expected

    def test_keeps_percent_inside_literal(self):
        sql = "SELECT '100% complete' AS progress FROM projects WHERE id = ?"
        expected = "SELECT '100% complete' AS progress FROM projects WHERE id = %s"
        assert to_pg_sql(sql) == expected

    def test_escapes_percent_outside_literal(self):
        # Outside literal: modulo operator or raw format string must escape % -> %%
        sql = "SELECT id % 10 FROM items WHERE status = ?"
        expected = "SELECT id %% 10 FROM items WHERE status = %s"
        assert to_pg_sql(sql) == expected

    def test_both_question_mark_and_percent_inside_literal(self):
        sql = "SELECT '100% genuine ?' FROM t WHERE x = ? AND y = ?"
        expected = "SELECT '100% genuine ?' FROM t WHERE x = %s AND y = %s"
        assert to_pg_sql(sql) == expected

    def test_doubled_quote_escape_inside_literal(self):
        sql = "SELECT 'It''s 100% ready?' FROM t WHERE name = ?"
        expected = "SELECT 'It''s 100% ready?' FROM t WHERE name = %s"
        assert to_pg_sql(sql) == expected

    def test_double_quoted_identifiers_and_literals(self):
        sql = 'SELECT "column_name" FROM "my_table" WHERE status = ? AND desc = \'?\''
        expected = 'SELECT "column_name" FROM "my_table" WHERE status = %s AND desc = \'?\''
        assert to_pg_sql(sql) == expected


class TestRow:
    """Verify Row dict and positional access."""

    def test_dict_access(self):
        r = Row(["id", "name", "role"], [1, "Ananya", "qc_lead"])
        assert r["id"] == 1
        assert r["name"] == "Ananya"
        assert r.get("role") == "qc_lead"
        assert "name" in r
        assert list(r.keys()) == ["id", "name", "role"]

    def test_positional_access(self):
        r = Row(["id", "name", "role"], [1, "Ananya", "qc_lead"])
        assert r[0] == 1
        assert r[1] == "Ananya"
        assert r[2] == "qc_lead"
        assert r[-1] == "qc_lead"
        assert r[:2] == (1, "Ananya")


class TestSessionAndSchema:
    """Verify Session operations, commit/rollback, and master checklist loading on fresh SQLite DB."""

    @pytest.fixture
    def fresh_session(self):
        conn = sqlite3.connect(":memory:")
        s = Session(conn, "sqlite")
        init_schema(s)
        yield s
        conn.close()

    def test_schema_init_idempotent(self, fresh_session):
        # Running init_schema again should not raise errors
        init_schema(fresh_session)
        assert fresh_session.scalar("SELECT COUNT(*) FROM organizations") == 0

    def test_master_checklist_load(self, fresh_session):
        count = load_master_checklist(fresh_session)
        assert count == 859
        stages = fresh_session.scalar("SELECT COUNT(*) FROM master_stages")
        subgroups = fresh_session.scalar("SELECT COUNT(*) FROM master_subgroups")
        checkpoints = fresh_session.scalar("SELECT COUNT(*) FROM master_checkpoints")
        assert stages == 20
        assert subgroups == 98
        assert checkpoints == 859

    def test_session_commit_and_rollback(self):
        conn = sqlite3.connect(":memory:")
        s = Session(conn, "sqlite")
        s.execute("CREATE TABLE test_tx (id INT, val TEXT)")
        s.execute("INSERT INTO test_tx VALUES (?, ?)", (1, "initial"))
        s.commit()

        # Verify inserted
        row = s.one("SELECT val FROM test_tx WHERE id = ?", (1,))
        assert row[0] == "initial"

        # Begin second insert then rollback
        s.execute("INSERT INTO test_tx VALUES (?, ?)", (2, "reverted"))
        s.rollback()

        row2 = s.one("SELECT val FROM test_tx WHERE id = ?", (2,))
        assert row2 is None

        conn.close()

    def test_in_clause_helper(self, fresh_session):
        assert fresh_session.in_clause(["a", "b", "c"]) == "?,?,?"
        assert fresh_session.in_clause([]) == "NULL"
