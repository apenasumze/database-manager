from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy.schema import MetaData
from typing import Type, Any
import pandas as pd
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm import declarative_base
from contextlib import contextmanager

class _SQLRaw:
    """Encapsula o resultado de uma query SQL Raw para permitir conversão em um pandas DataFrame."""
    def __init__(self, data: list):
        self._data = data

    def to_df(self) -> pd.DataFrame:
        """Converte os dados brutos em um DataFrame do Pandas."""
        return pd.DataFrame(self._data)
    
    def __repr__(self):
        return str(self._data)

class _Query(Query):
    """Extensão da classe Query do SQLAlchemy com injeção dafuncionalidade de conversão para um pandas DataFrame."""
    
    def to_df(self, **kwargs) -> pd.DataFrame:
        """
        Converte o resultado da consulta atual em um DataFrame do Pandas.
        Aceita qualquer argumento válido do construtor pd.DataFrame().
        
        Extrai o statement e o bind da sessão vinculada para realizar a leitura 
        direta via banco de dados, encerrando a sessão após a operação.

        Returns:
            pd.DataFrame: Resultado da consulta em formato tabular.
        """
        try:
            # A própria instância (self) é o objeto Query
            df = pd.read_sql(self.statement, self.session.bind)
            return df
        finally:
            self.session.close()

class DatabaseManager:
    """
    Classe para gerenciamento de conexões com bancos de dados diversos via SQLAlchemy ORM.
    Compatível com múltiplos bancos (PostgreSQL, SQLite, MySQL, etc).
    """

    def __init__(self, database_url: str, base_models: DeclarativeMeta = None, echo_queries: bool = False) -> None:
        """
        Inicializa o gerenciador de banco de dados.

        Args:
            database_url (str): URL do banco (ex: sqlite://, postgresql://...)
            base_models (DeclarativeMeta): Base declarativa do SQLAlchemy. Se fornecida, serão criadas as tabelas no banco de dados. Defaults to None.
            echo_queries (bool): Exibe as queries executadas. Defaults to False.
        """
        self.engine: Engine = create_engine(database_url, echo=echo_queries)
        self.Session = scoped_session(sessionmaker(bind=self.engine, query_cls=_Query))

        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                print(f"[INFO] Banco de dados conectado.")

                if base_models:
                    print("[INFO] Criando tabelas no banco de dados.")
                    self.create_all(base_models.metadata)
        except SQLAlchemyError as e:
            print(f"[Erro de conexão ao banco]: {e}")

    @staticmethod
    def build_url(driver: str, database: str, user: str = None, 
                  password: str = None, host: str = None, port: str = None) -> str:
        r"""Constrói a string de conexão ao banco de dados conforme padrão SQLAlchemy com suporte a caminhos UNC.

        Este método formata URLs de conexão para diversos drivers, com tratamentoespecial para SQLite, 
        permitindo tanto arquivos locais quanto arquivos em pastas de rede Windows (caminhos UNC). 
        Para MSSQL, anexa automaticamente o driver ODBC 17.

        Args:
            driver (str): O driver do banco de dados (ex: 'sqlite', 'postgresql', 'mysql', 'mssql+pyodbc').
            database (str): Nome do banco de dados ou caminho do arquivo se for SQLite.
            user (Optional[str]): Nome de usuário para autenticação. Defaults to None.
            password (Optional[str]): Senha para autenticação. Defaults to None.
            host (Optional[str]): Endereço do servidor (ex: 'localhost' ou IP). Defaults to None.
            port (Optional[str]): Porta de conexão (ex: '5432', '1433'). Defaults to None.

        Returns:
            str: Uma URL de conexão formatada e pronta para o SQLAlchemy.

        Examples:
            >>> # SQLite Local
            >>> DatabaseManager.build_url('sqlite', 'C:/dados/meubanco.db')
            'sqlite:///C:/dados/meubanco.db'

            >>> # SQLite Rede (UNC)
            >>> DatabaseManager.build_url('sqlite', r'\\SERVIDOR\compartilhada\db.sqlite')
            'sqlite:////SERVIDOR/compartilhada/db.sqlite'

            >>> # SQL Server (MSSQL)
            >>> DatabaseManager.build_url('mssql+pyodbc', 'SIVWIN', 'sa', '123', '192.168.1.10', '1433')
            'mssql+pyodbc://sa:123@192.168.1.10:1433/SIVWIN?driver=ODBC+Driver+17+for+SQL+Server'
        """            
        if driver.lower() == 'sqlite':
            path = database.replace('\\', '/')
            if database.startswith('\\\\'):
                while path.startswith('/'): path = path[1:]
                return f"sqlite:////{path}"
            return f"sqlite:///{path}"
    
        # Construção inteligente para evitar "None" na string
        auth = f"{user}:{password}@" if user and password else ""
        
        # Só adiciona a porta se ela for informada e não for vazia
        host_part = f"{host}" if host else "localhost"
        if port and str(port).lower() != 'none':
            host_part += f":{port}"
    
        db_url = f"{driver}://{auth}{host_part}/{database}"
        
        if driver == "mssql+pyodbc":
            db_url += "?driver=ODBC+Driver+17+for+SQL+Server"
            
        return db_url

    @contextmanager
    def session(self):
        """Gerenciador de contexto interno para operações automáticas."""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def sql_raw(self, query: str, params: dict = None) -> _SQLRaw:
        """Executa instruções SQL puras e retorna os registros encontrados.

        Este método utiliza uma sessão de escopo curto para executar comandos SQL diretamente no banco de dados. 
        É ideal para consultas complexas que não são facilmente mapeadas via ORM ou para comandos rápidos. 
        O commit e o fechamento da sessão são gerenciados automaticamente.

        Args:
            query (str): Instrução SQL a ser executada (ex: SELECT, UPDATE, etc).
            params (Optional[dict]): Dicionário contendo os parâmetros para a instrução SQL, prevenindo SQL Injection. Defaults to None.

        Returns:
            Any: Uma lista de objetos Row (tuplas nomeadas) contendo o resultado 
                da consulta. Retorna uma lista vazia se não houver resultados.

        Example:
            >>> db.sql_raw("SELECT * FROM usuarios WHERE ativo = :status", {"status": 1})
            [(1, 'Joaquim', 1), (2, 'Gustavo', 1)]
        """
        with self.session() as session:
            result = session.execute(text(query), params or {})
            return _SQLRaw(result.all())

    def orm(self, model: Type[Any]) -> _Query:
        """Inicia uma consulta ORM nativa do SQLAlchemy.

        Este método fornece a porta de entrada para a interface fluente do SQLAlchemy, permitindo o encadeamento de filtros, ordenações e joins diretamente no modelo especificado. A sessão é gerenciada pelo scoped_session da classe.

        Args:
            model (Type): A classe do modelo mapeado (herdada de Base) sobre a qual a consulta será realizada.

        Returns:
            sqlalchemy.orm.Query: Um objeto de consulta nativo que suporta métodos como .filter(), .order_by(), .limit() e .all().

        Example:
            >>> query = db.orm(Veiculo).filter(Veiculo.placa == 'ABC1234')
            >>> resultado = query.first()
        """
        return self.Session().query(model)

    # --- MÉTODOS DE METADATA ---

    def create_all(self, base_metadata: MetaData) -> None:
        """Cria todas as tabelas definidas no metadado fornecido.

        Utiliza a engine configurada para emitir comandos DDL (Data Definition Language) ao banco de dados, 
        criando as estruturas físicas das tabelas que ainda não existem.

        Args:
            base_metadata (MetaData): Objeto de metadados do SQLAlchemy, geralmente obtido através de Base.metadata.
        """
        base_metadata.create_all(self.engine)

    def drop_all(self, base_metadata: MetaData) -> None:
        """Remove todas as tabelas definidas no metadado fornecido.

        Emite comandos de exclusão (DROP TABLE) para todas as tabelas mapeadas. 
        Operação destrutiva utilizada principalmente em ambientes de teste para limpeza de schema.

        Args:
            base_metadata (MetaData): Objeto de metadados do SQLAlchemy, geralmente obtido através de Base.metadata.
        """
        base_metadata.drop_all(self.engine)
        
