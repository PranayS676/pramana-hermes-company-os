from __future__ import annotations

from hermes_company_os.database import (
    SCHEMA_VERSION,
    connect,
    ensure_schema,
    get_schema_version,
    initialize_database,
    set_schema_version,
)


def test_schema_version_is_a_positive_integer():
    assert isinstance(SCHEMA_VERSION, int)
    assert SCHEMA_VERSION >= 1


def test_initialize_database_stamps_current_schema_version(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    with connect(database_path) as connection:
        assert get_schema_version(connection) == SCHEMA_VERSION


def test_initialize_database_is_idempotent_and_keeps_version(tmp_path):
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    # Re-running must not change the stamped version or lose seeded data.
    initialize_database(database_path)
    with connect(database_path) as connection:
        assert get_schema_version(connection) == SCHEMA_VERSION
        agent_count = connection.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        assert agent_count > 0


def test_ensure_schema_restamps_an_unversioned_database(tmp_path):
    # Simulate a pre-versioning database: tables exist but user_version is 0.
    database_path = tmp_path / "company.db"
    initialize_database(database_path)
    with connect(database_path) as connection:
        set_schema_version(connection, 0)
    with connect(database_path) as connection:
        assert get_schema_version(connection) == 0

    with connect(database_path) as connection:
        ensure_schema(connection)
    with connect(database_path) as connection:
        assert get_schema_version(connection) == SCHEMA_VERSION
        # Existing data survives the re-stamp.
        agent_count = connection.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
        assert agent_count > 0


def test_set_and_get_schema_version_round_trip(tmp_path):
    database_path = tmp_path / "company.db"
    with connect(database_path) as connection:
        set_schema_version(connection, 7)
        assert get_schema_version(connection) == 7
