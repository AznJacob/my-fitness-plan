from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.models import Base


def test_initial_schema_registers_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        "authentication_identities",
        "plans",
        "profiles",
        "users",
    }


def test_initial_schema_compiles_for_postgresql() -> None:
    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]

    for table in Base.metadata.sorted_tables:
        statement = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table.name}" in statement


def test_ownership_foreign_keys_delete_dependent_data() -> None:
    for table_name in ("authentication_identities", "profiles", "plans"):
        foreign_keys = Base.metadata.tables[table_name].foreign_keys
        assert len(foreign_keys) == 1
        foreign_key = next(iter(foreign_keys))
        assert foreign_key.target_fullname == "users.id"
        assert foreign_key.ondelete == "CASCADE"


def test_plan_schema_enforces_one_active_plan_per_user() -> None:
    plans = Base.metadata.tables["plans"]
    active_plan_index = next(
        index for index in plans.indexes if index.name == "uq_plans_one_active_per_user"
    )

    assert active_plan_index.unique is True
    assert str(active_plan_index.dialect_options["postgresql"]["where"]) == "status = 'active'"


def test_authentication_schema_enforces_identity_safety_constraints() -> None:
    identities = Base.metadata.tables["authentication_identities"]
    constraint_names = {constraint.name for constraint in identities.constraints}

    assert {
        "ck_authentication_identities_password_hash",
        "uq_authentication_identities_provider_subject",
        "uq_authentication_identities_user_provider",
    } <= constraint_names

    password_email_index = next(
        index
        for index in identities.indexes
        if index.name == "uq_authentication_identities_password_email"
    )
    assert password_email_index.unique is True
    assert (
        str(password_email_index.dialect_options["postgresql"]["where"]) == "provider = 'password'"
    )
