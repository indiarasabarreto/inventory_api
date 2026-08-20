"""Migra dados do inventory.db local para PostgreSQL preservando IDs e relações.

Use primeiro com --dry-run para revisar as contagens. A transferência real só ocorre
quando o argumento --apply é informado explicitamente.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence

import sqlalchemy as sa
from dotenv import load_dotenv


SOURCE_URL = "sqlite:///./inventory.db"
TABLES: Sequence[str] = ("categories", "products", "stock_movements")


def configured_target_url() -> str:
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url.startswith("postgresql"):
        raise SystemExit(
            "DATABASE_URL precisa apontar para PostgreSQL no arquivo .env antes da migração."
        )

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )

    return database_url


def table_rows(engine: sa.Engine, table_name: str) -> list[dict[str, object]]:
    metadata = sa.MetaData()
    table = sa.Table(table_name, metadata, autoload_with=engine)

    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(sa.select(table)).mappings()]


def counts(engine: sa.Engine) -> dict[str, int]:
    result: dict[str, int] = {}
    for table_name in TABLES:
        with engine.connect() as connection:
            result[table_name] = connection.scalar(
                sa.text(f"SELECT COUNT(*) FROM {table_name}")
            ) or 0
    return result


def print_counts(title: str, values: dict[str, int]) -> None:
    joined = ", ".join(f"{table}={count}" for table, count in values.items())
    print(f"{title}: {joined}")


def reset_sequence(connection: sa.Connection, table_name: str) -> None:
    connection.execute(
        sa.text(
            "SELECT setval("
            "pg_get_serial_sequence(:table_name, 'id'), "
            "COALESCE((SELECT MAX(id) FROM " + table_name + "), 1), true)"
        ),
        {"table_name": table_name},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="confirma a transferência real após a revisão das contagens",
    )
    arguments = parser.parse_args()

    source_engine = sa.create_engine(
        SOURCE_URL, connect_args={"check_same_thread": False}
    )
    target_engine = sa.create_engine(configured_target_url(), pool_pre_ping=True)

    source_rows = {table_name: table_rows(source_engine, table_name) for table_name in TABLES}
    source_counts = {table_name: len(rows) for table_name, rows in source_rows.items()}
    target_counts = counts(target_engine)

    print_counts("Dados no SQLite local", source_counts)
    print_counts("Dados atuais no PostgreSQL", target_counts)

    if not arguments.apply:
        print("Dry run concluído. Nenhum dado foi transferido.")
        return

    if any(target_counts.values()):
        raise SystemExit(
            "O PostgreSQL já possui dados. Migração cancelada para evitar duplicação."
        )

    target_metadata = sa.MetaData()
    target_tables = {
        table_name: sa.Table(table_name, target_metadata, autoload_with=target_engine)
        for table_name in TABLES
    }

    with target_engine.begin() as connection:
        for table_name in TABLES:
            rows = source_rows[table_name]
            if rows:
                connection.execute(target_tables[table_name].insert(), rows)

        for table_name in TABLES:
            if source_rows[table_name]:
                reset_sequence(connection, table_name)

    final_counts = counts(target_engine)
    print_counts("Dados transferidos ao PostgreSQL", final_counts)

    if final_counts != source_counts:
        raise SystemExit(
            "As contagens não coincidem. Revise o PostgreSQL antes de continuar."
        )

    print("Migração concluída com sucesso. IDs, relações e contagens foram preservados.")


if __name__ == "__main__":
    main()
