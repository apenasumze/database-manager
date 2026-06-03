import logging
from contextlib import contextmanager
from typing import Any, Mapping, Sequence, Type
from urllib.parse import quote, urlencode

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, scoped_session, sessionmaker
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.schema import MetaData


logger = logging.getLogger(__name__)


class _SQLRaw:
    """Encapsula o resultado de uma consulta SQL raw."""

    def __init__(self, data: list, columns: list[str] = None):
        self._data = data
        self._columns = columns

    def to_df(self, **kwargs) -> pd.DataFrame:
        """Converte os dados brutos em um DataFrame do Pandas."""
        kwargs.setdefault("columns", self._columns)
        return pd.DataFrame(self._data, **kwargs)

    def __repr__(self):
        return str(self._data)


class _Query(Query):
    """Extensao de Query com conversao direta para DataFrame."""

    def to_df(self, **kwargs) -> pd.DataFrame:
        """Converte o resultado da consulta atual em um DataFrame do Pandas."""
        try:
            return pd.read_sql(self.statement, self.session.bind, **kwargs)
        finally:
            self.session.close()


class DatabaseManager:
    """Gerencia conexoes com bancos de dados via SQLAlchemy."""

    def __init__(
        self,
        database_url: str,
        base_models: DeclarativeMeta = None,
        echo_queries: bool = False,
        validate_connection: bool = True,
    ) -> None:
        """Inicializa o gerenciador de banco de dados.

        Args:
            database_url: URL SQLAlchemy do banco.
            base_models: Base declarativa. Se fornecida, cria as tabelas.
            echo_queries: Exibe as queries executadas pelo SQLAlchemy.
            validate_connection: Valida a conexao na inicializacao.
        """
        self.engine: Engine = create_engine(database_url, echo=echo_queries)
        self.Session = scoped_session(sessionmaker(bind=self.engine, query_cls=_Query))

        if validate_connection:
            self._validate_connection()

        if base_models:
            logger.debug("Criando tabelas no banco de dados.")
            self.create_all(base_models.metadata)

    def _validate_connection(self) -> None:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError:
            logger.exception("Erro de conexao ao banco de dados.")
            raise

    @staticmethod
    def build_url(
        driver: str,
        database: str,
        user: str = None,
        password: str = None,
        host: str = None,
        port: str = None,
        query_params: Mapping[str, str] = None,
        odbc_driver: str = "ODBC Driver 18 for SQL Server",
    ) -> str:
        r"""Constroi uma URL SQLAlchemy com tratamento para SQLite e encoding seguro.

        Args:
            driver: Driver SQLAlchemy, como sqlite, postgresql, mysql ou mssql+pyodbc.
            database: Nome do banco ou caminho do arquivo SQLite.
            user: Usuario de conexao.
            password: Senha de conexao.
            host: Endereco do servidor.
            port: Porta de conexao.
            query_params: Parametros extras da URL.
            odbc_driver: Driver ODBC usado quando driver="mssql+pyodbc".
        """
        driver_name = driver.strip()
        if "://" in driver_name:
            driver_name = driver_name.split("://", 1)[0]

        if driver_name.lower().startswith("sqlite"):
            path = database.replace("\\", "/")
            if database.startswith("\\\\"):
                return f"{driver_name}:////{path.lstrip('/')}"
            return f"{driver_name}:///{path}"

        params = dict(query_params or {})
        if driver_name == "mssql+pyodbc" and "driver" not in params:
            params["driver"] = odbc_driver

        auth = ""
        if user is not None:
            auth = quote(user, safe="")
            if password is not None:
                auth += f":{quote(password, safe='')}"
            auth += "@"

        netloc = host or ""
        if port is not None:
            netloc += f":{port}"

        url = f"{driver_name}://{auth}{netloc}/{quote(database, safe='/')}"
        if params:
            url += f"?{urlencode(params)}"
        return url

    @contextmanager
    def session(self):
        """Gerenciador de contexto para operacoes transacionais."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _normalize_sql_params(
        sql: str,
        params: Mapping[str, Any] | Sequence[Any] = None,
    ) -> tuple[str, Mapping[str, Any] | None]:
        if not isinstance(params, (list, tuple)):
            return sql, params

        normalized_params = {}
        normalized_sql = sql
        for index, value in enumerate(params):
            param_name = f"param_{index}"
            normalized_params[param_name] = value

            if "?" in normalized_sql:
                normalized_sql = normalized_sql.replace("?", f":{param_name}", 1)
            elif "%s" in normalized_sql:
                normalized_sql = normalized_sql.replace("%s", f":{param_name}", 1)

        return normalized_sql, normalized_params

    def query(
        self,
        sql: str,
        params: Mapping[str, Any] | Sequence[Any] = None,
    ) -> _SQLRaw:
        """Executa uma consulta SQL raw e retorna os registros encontrados."""
        sql, params = self._normalize_sql_params(sql, params)
        with self.session() as session:
            result = session.execute(text(sql), params or {})
            columns = list(result.keys())
            return _SQLRaw(result.mappings().all(), columns=columns)

    def sql_raw(
        self,
        query: str,
        params: Mapping[str, Any] | Sequence[Any] = None,
    ) -> _SQLRaw:
        """Alias de compatibilidade para query()."""
        return self.query(query, params)

    def sql_raw_select(
        self,
        query: str,
        params: Mapping[str, Any] | Sequence[Any] = None,
    ) -> _SQLRaw:
        """Alias explicito para consultas SQL raw com retorno tabular."""
        return self.query(query, params)

    def execute(
        self,
        sql: str,
        params: Mapping[str, Any] | Sequence[Any] = None,
    ) -> int:
        """Executa um comando SQL sem retorno tabular."""
        sql, params = self._normalize_sql_params(sql, params)
        with self.session() as session:
            result = session.execute(text(sql), params or {})
            return result.rowcount

    def execute_many(self, sql: str, params_list: Sequence[Mapping[str, Any]]) -> int:
        """Executa um comando SQL para uma sequencia de parametros."""
        with self.session() as session:
            result = session.execute(text(sql), params_list)
            return result.rowcount

    def orm(self, model: Type[Any]) -> _Query:
        """Inicia uma consulta ORM nativa do SQLAlchemy."""
        return self.Session().query(model)

    def create_all(self, base_metadata: MetaData) -> None:
        """Cria todas as tabelas definidas no metadado fornecido."""
        base_metadata.create_all(self.engine)

    def drop_all(self, base_metadata: MetaData) -> None:
        """Remove todas as tabelas definidas no metadado fornecido."""
        base_metadata.drop_all(self.engine)
