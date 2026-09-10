from pathlib import Path

MIGRATION = Path("supabase/migrations/20260810033029_guildpilot_core.sql")


def test_every_public_table_has_rls_enabled() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()
    tables = [
        "guilds",
        "guild_memberships",
        "module_configs",
        "tickets",
        "audit_log",
        "analytics_events",
        "outbox",
        "jobs",
    ]

    for table in tables:
        assert f"alter table public.{table} enable row level security;" in sql


def test_browser_roles_are_revoked_and_service_role_is_explicit() -> None:
    sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "revoke all on all tables in schema public from anon, authenticated;" in sql
    server_grant = (
        "grant select, insert, update, delete on all tables in schema public to service_role;"
    )
    assert server_grant in sql
    assert "security invoker" in sql
    assert "security definer" not in sql
