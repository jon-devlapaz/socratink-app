from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = REPO_ROOT / "db" / "loop_sessions.sql"


def test_loop_sessions_schema_is_rls_scoped_and_concurrency_ready() -> None:
    sql = SCHEMA.read_text()

    assert "user_id UUID NOT NULL DEFAULT auth.uid()" in sql
    assert "ALTER TABLE public.loop_sessions ENABLE ROW LEVEL SECURITY" in sql
    assert 'CREATE POLICY "loop_sessions_select_own"' in sql
    assert 'CREATE POLICY "loop_sessions_insert_own"' in sql
    assert 'CREATE POLICY "loop_sessions_update_own"' in sql
    assert 'CREATE POLICY "loop_sessions_delete_own"' in sql
    assert sql.count("auth.uid() = user_id") >= 4
    assert "version BIGINT NOT NULL DEFAULT 0" in sql
    assert "turn_receipts JSONB NOT NULL DEFAULT '[]'::jsonb" in sql
    assert "last_request_id" not in sql
    assert "loop_sessions_user_id_idx" in sql
    assert "loop_sessions_expires_at_idx" in sql
    assert "purge_expired_loop_sessions" in sql
    assert "FROM PUBLIC, anon, authenticated" in sql


def test_loop_sessions_schema_bounds_journal_and_replay_payloads() -> None:
    sql = SCHEMA.read_text()

    assert "jsonb_array_length(events) <= 128" in sql
    assert "octet_length(events::text) <= 524288" in sql
    assert "octet_length(metadata::text) <= 262144" in sql
    assert "jsonb_array_length(metadata -> 'transcript_tail') <= 80" in sql
    assert "jsonb_array_length(turn_receipts) <= 16" in sql
    assert "octet_length(turn_receipts::text) <= 2097152" in sql
    assert "REVOKE ALL ON public.loop_sessions FROM PUBLIC, anon" in sql
    assert "service_role" not in sql.lower()
