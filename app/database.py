import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Localmente, usa o banco atual na raiz do projeto.
# Na Railway, usará o valor definido na variável DATABASE_URL.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inventory.db")
REQUIRE_POSTGRESQL = os.getenv("REQUIRE_POSTGRESQL", "false").lower() == "true"

if REQUIRE_POSTGRESQL and not DATABASE_URL.startswith("postgresql"):
    raise RuntimeError(
        "REQUIRE_POSTGRESQL=true exige uma DATABASE_URL PostgreSQL válida."
    )

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class Base(DeclarativeBase):
    pass
