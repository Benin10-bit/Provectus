from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os


# Agora a URL será montada corretamente para o ambiente Docker
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+psycopg://provectususer:1992@localhost:5432/provectusdb"
)

# 2. Criação do Engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 3. Configuração da Sessão
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Base para os Models
Base = declarative_base()

# Dependência para as rotas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()