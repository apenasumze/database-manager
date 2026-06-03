import pytest
from sqlalchemy import text

from databasemanager import DatabaseManager


def test_package_exports_database_manager():
    assert DatabaseManager.__name__ == "DatabaseManager"


def test_build_url_sqlite_local_path():
    assert (
        DatabaseManager.build_url("sqlite", "C:/dados/app.db")
        == "sqlite:///C:/dados/app.db"
    )


def test_build_url_accepts_sqlite_url_style_driver():
    assert (
        DatabaseManager.build_url("sqlite://", "C:/dados/app.db")
        == "sqlite:///C:/dados/app.db"
    )


def test_build_url_sqlite_unc_path():
    assert (
        DatabaseManager.build_url("sqlite", r"\\SERVIDOR\compartilhada\db.sqlite")
        == "sqlite:////SERVIDOR/compartilhada/db.sqlite"
    )


def test_build_url_encodes_credentials_and_database():
    assert (
        DatabaseManager.build_url(
            "postgresql+psycopg2",
            "base dados",
            user="user@email.com",
            password="p@ss:word",
            host="localhost",
            port="5432",
        )
        == "postgresql+psycopg2://user%40email.com:p%40ss%3Aword@localhost:5432/base%20dados"
    )


def test_build_url_mssql_adds_default_odbc_driver():
    assert (
        DatabaseManager.build_url(
            "mssql+pyodbc",
            "SIVWIN",
            user="sa",
            password="123",
            host="192.168.1.10",
            port="1433",
        )
        == "mssql+pyodbc://sa:123@192.168.1.10:1433/SIVWIN?driver=ODBC+Driver+18+for+SQL+Server"
    )


def test_sqlite_query_to_df_preserves_column_names():
    db = DatabaseManager("sqlite:///:memory:")

    db.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, ativo INTEGER)")
    db.execute(
        "INSERT INTO usuarios (nome, ativo) VALUES (:nome, :ativo)",
        {"nome": "Jose", "ativo": 1},
    )

    df = db.query("SELECT id, nome FROM usuarios WHERE ativo = :ativo", {"ativo": 1}).to_df()

    assert list(df.columns) == ["id", "nome"]
    assert df.to_dict("records") == [{"id": 1, "nome": "Jose"}]


def test_sqlite_query_accepts_positional_question_mark_params():
    db = DatabaseManager("sqlite:///:memory:")

    db.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, ativo INTEGER)")
    db.execute(
        "INSERT INTO usuarios (nome, ativo) VALUES (?, ?)",
        ["Jose", 1],
    )

    df = db.query("SELECT nome FROM usuarios WHERE ativo = ?", [1]).to_df()

    assert df.to_dict("records") == [{"nome": "Jose"}]


def test_sqlite_query_accepts_positional_percent_s_params():
    db = DatabaseManager("sqlite:///:memory:")

    db.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, ativo INTEGER)")
    db.execute(
        "INSERT INTO usuarios (nome, ativo) VALUES (%s, %s)",
        ("Jose", 1),
    )

    df = db.query("SELECT nome FROM usuarios WHERE ativo = %s", (1,)).to_df()

    assert df.to_dict("records") == [{"nome": "Jose"}]


def test_sqlite_query_to_df_preserves_columns_when_empty():
    db = DatabaseManager("sqlite:///:memory:")

    db.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT)")
    df = db.query("SELECT id, nome FROM usuarios WHERE id = :id", {"id": 999}).to_df()

    assert list(df.columns) == ["id", "nome"]
    assert df.empty


def test_sqlite_execute_many_inserts_batch():
    db = DatabaseManager("sqlite:///:memory:")

    db.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT)")
    db.execute_many(
        "INSERT INTO usuarios (nome) VALUES (:nome)",
        [{"nome": "Jose"}, {"nome": "Maria"}],
    )

    df = db.query("SELECT nome FROM usuarios ORDER BY id").to_df()

    assert df.to_dict("records") == [{"nome": "Jose"}, {"nome": "Maria"}]


def test_session_rolls_back_on_error():
    db = DatabaseManager("sqlite:///:memory:")

    db.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT)")

    with pytest.raises(RuntimeError):
        with db.session() as session:
            session.execute(text("INSERT INTO usuarios (nome) VALUES (:nome)"), {"nome": "Jose"})
            raise RuntimeError("forcar rollback")

    df = db.query("SELECT id, nome FROM usuarios").to_df()

    assert df.empty
