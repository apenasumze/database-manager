DatabaseManager

DatabaseManager é um componente de infraestrutura Python desenvolvido para simplificar a interação com múltiplos bancos de dados (PostgreSQL, SQL Server, MySQL, SQLite) através de uma interface fluida, simétrica e totalmente integrada ao Pandas.

🚀 Diferenciais do Projeto
Simetria Total: Mesma experiência de uso simultâneo para consultas ORM e SQL Puro.

Conversão Nativa: Método .to_df() injetado diretamente para obtenção rápida de dataframes.

Gestão de Conexões: Gerenciamento automático de sessões (scoped sessions) e encerramento de conexões após a conversão para DataFrame.

Suporte UNC: Compatibilidade nativa com caminhos de rede Windows (especial para bancos SQLite em rede).

🛠️ Tecnologias Utilizadas
SQLAlchemy 2.0+: Motor de persistência e ORM.

Pandas: Estruturação de dados tabulares.

Python 3.10+: Tipagem moderna e performance.

📋 Como Utilizar
1. Inicialização e Conexão
from databasemanager import DatabaseManager

A biblioteca fornece um metodo estático para criar a URL de conexão ao banco de dados automaticamente.

# Construção de URL com suporte a SQL Server (UNC/Rede)
url = DatabaseManager.build_url(
    driver='mssql+pyodbc',
    host='IP ou nome do servidor / caminho UNC / localhost',
    database='nome do banco de dados',
    user='nome de usuário',
    password='senha',
)

# Construção de URL com suporte a PostgreSQL
url = DatabaseManager.build_url(
    driver='postgresql+psycopg2',
    host='IP ou nome do servidor / caminho UNC / localhost',
    database='nome do banco de dados',
    user='nome de usuário',
    password='senha',
)

# Construção de URL com suporte a MySQL
url = DatabaseManager.build_url(
    driver='mysql+pymysql',
    host='IP ou nome do servidor / caminho UNC / localhost',
    database='nome do banco de dados',
    user='nome de usuário',
    password='senha',
)

# Construção de URL com suporte a SQLite
url = DatabaseManager.build_url(
    driver='sqlite://',
    database='caminho do banco de dados',
)

# Criada a string de conexão ao banco de dados, utiliza-a para criar o gerenciador de banco de dados.
dbm = DatabaseManager(url)

2. Gerenciamento de Models
Pode-se utilizar um Base declarativo para  interagir com modelos de  tabelas no banco de dados.

from databasemanager import DatabaseManager
from models import Base

dbm = DatabaseManager("sqlite:///:memory:")
dbm.create_all(Base.metadata)
dbm.drop_all(Base.metadata)


3. Simetria de Interface
O grande poder desta biblioteca reside na facilidade de transformar qualquer consulta em um DataFrame sem argumentos adicionais no final da cadeia.

Via ORM 
query = dbm.orm(Usuario).filter(Usuario.nome.like('%Jose%')) # Objeto query
df = query.to_df() # Transformação direta para DataFrame

Via SQL Raw (Puro)
query = dbm.sql_raw("SELECT * FROM usuarios WHERE ativo = 1") # Lista de tuplas no padrão SQL puro
df = query.to_df() # Transformação direta para DataFrame

Pode-se encadear as operações se o resultado esperado for direto em um DataFrame.
df = dbm.sql_raw("SELECT * FROM usuarios WHERE ativo = 1").to_df()
df = dbm.orm(Usuario).filter(Usuario.ativo == 1).to_df()


4. Operações Transacionais (Escopo de Sessão)
Para operações de escrita (Insert/Update/Delete), utilize o gerenciador de contexto que garante o commit e close automáticos.

Python
with dbm.session() as s:
    novo_usuario = Usuario(nome="Jose Vitor")
    s.add(novo_usuario)

⚙️ Instalação Local
Para instalar em modo de desenvolvimento no seu ambiente:


Bash
# Clone o repositório e na raiz execute:
pip install -e .


📝 Licença
Este projeto foi desenvolvido por Jose Vitor Alves Coelho.