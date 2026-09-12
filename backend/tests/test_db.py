from app.db import normalize_database_url


def test_postgres_urls_get_the_psycopg_dialect():
    assert normalize_database_url("postgres://u:p@host:5432/db") == "postgresql+psycopg://u:p@host:5432/db"
    assert normalize_database_url("postgresql://u:p@host:5432/db") == "postgresql+psycopg://u:p@host:5432/db"


def test_other_urls_pass_through():
    assert normalize_database_url("sqlite:///./cheffy.db") == "sqlite:///./cheffy.db"
    assert normalize_database_url("postgresql+psycopg://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
