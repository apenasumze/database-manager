# Full DB Manager

`full-db-manager` e uma biblioteca Python para simplificar conexoes SQLAlchemy,
consultas SQL raw, consultas ORM e conversao direta de resultados para
`pandas.DataFrame`.

## Recursos

- Interface simples para SQL raw e ORM.
- Conversao direta para DataFrame com `.to_df()`.
- Gerenciamento transacional por contexto com commit e rollback automaticos.
- Suporte a SQLite local e caminhos UNC no Windows.
- Drivers de banco separados por extras opcionais.

## Instalacao

Instalacao base:

```bash
pip install full-db-manager
```

Drivers opcionais:

```bash
pip install "full-db-manager[mssql]"
pip install "full-db-manager[postgres]"
pip install "full-db-manager[mysql]"
```

Ambiente de desenvolvimento:

```bash
pip install -e ".[dev]"
```

## Uso Basico

```python
from databasemanager import DatabaseManager

url = DatabaseManager.build_url("sqlite", "app.db")
db = DatabaseManager(url)

db.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nome TEXT, ativo INTEGER)")
db.execute(
    "INSERT INTO usuarios (nome, ativo) VALUES (:nome, :ativo)",
    {"nome": "Jose", "ativo": 1},
)

df = db.query("SELECT id, nome FROM usuarios WHERE ativo = :ativo", {"ativo": 1}).to_df()
```

## URLs de Conexao

SQLite local:

```python
url = DatabaseManager.build_url("sqlite", "C:/dados/app.db")
```

SQLite em caminho UNC:

```python
url = DatabaseManager.build_url("sqlite", r"\\SERVIDOR\compartilhada\app.db")
```

SQL Server:

```python
url = DatabaseManager.build_url(
    "mssql+pyodbc",
    database="SIVWIN",
    user="sa",
    password="senha",
    host="192.168.1.10",
    port="1433",
)
```

PostgreSQL:

```python
url = DatabaseManager.build_url(
    "postgresql+psycopg",
    database="app",
    user="postgres",
    password="senha",
    host="localhost",
    port="5432",
)
```

MySQL:

```python
url = DatabaseManager.build_url(
    "mysql+pymysql",
    database="app",
    user="root",
    password="senha",
    host="localhost",
    port="3306",
)
```

## Consultas e Comandos

Use `query()` para consultas com retorno tabular:

```python
df = db.query("SELECT id, nome FROM usuarios").to_df()
```

Use `execute()` para comandos sem retorno tabular:

```python
linhas = db.execute(
    "UPDATE usuarios SET ativo = :ativo WHERE id = :id",
    {"ativo": 0, "id": 1},
)
```

Use `execute_many()` para execucao em lote:

```python
db.execute_many(
    "INSERT INTO usuarios (nome) VALUES (:nome)",
    [{"nome": "Jose"}, {"nome": "Maria"}],
)
```

`sql_raw()` permanece disponivel como alias de compatibilidade para `query()`.
Para novos usos, prefira `query()` ou `sql_raw_select()`.

## Sessoes ORM

```python
with db.session() as session:
    session.add(usuario)
```

Em caso de erro dentro do bloco, a transacao e revertida automaticamente.

## Validacao de Conexao

Por padrao, `DatabaseManager` valida a conexao na inicializacao e levanta a
excecao do SQLAlchemy se a conexao falhar.

```python
db = DatabaseManager(url, validate_connection=True)
```

Para adiar a conexao ate o primeiro uso:

```python
db = DatabaseManager(url, validate_connection=False)
```

## Testes

```bash
python -m pytest
```

## Licenca

Distribuido sob a licenca MIT.
