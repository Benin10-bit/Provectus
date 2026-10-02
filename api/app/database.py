import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

# URL.create escapes passwords correctly; DATABASE_URL remains supported locally.
url = os.getenv("DATABASE_URL")
if not url:
    required = ("DB_USER", "DB_PASSWORD", "DB_NAME")
    if any(not os.getenv(k) for k in required):
        raise RuntimeError("Configure DATABASE_URL ou DB_USER, DB_PASSWORD e DB_NAME.")
    url = URL.create("postgresql+psycopg", username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"], host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")), database=os.environ["DB_NAME"])
engine = create_engine(url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    with SessionLocal() as db:
        yield db
