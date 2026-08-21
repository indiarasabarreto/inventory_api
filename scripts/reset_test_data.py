"""Limpa dados de teste do PostgreSQL de forma explícita e verificável."""

import argparse
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text


TABLES = ("categories", "products", "stock_movements")


def read_counts(connection):
    return {
        table: connection.scalar(text(f"SELECT COUNT(*) FROM {table}"))
        for table in TABLES
    }


def main():
    parser = argparse.ArgumentParser(
        description="Limpa categorias, produtos e movimentações de teste."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Executa a limpeza após a confirmação textual.",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help="Digite exatamente LIMPAR_DADOS_DE_TESTE para confirmar.",
    )
    args = parser.parse_args()

    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "")

    if not database_url.startswith("postgresql"):
        raise RuntimeError("A limpeza exige uma DATABASE_URL PostgreSQL válida.")

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    engine = create_engine(database_url)

    with engine.connect() as connection:
        before = read_counts(connection)

    print("Dados atuais no PostgreSQL:")
    print(
        "categories={categories}, products={products}, "
        "stock_movements={stock_movements}".format(**before)
    )

    if not args.apply:
        print("Modo de revisão: nenhum dado foi removido.")
        return

    if args.confirm != "LIMPAR_DADOS_DE_TESTE":
        raise RuntimeError(
            "Confirmação inválida. Use --confirm LIMPAR_DADOS_DE_TESTE."
        )

    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE stock_movements, products, categories "
                "RESTART IDENTITY CASCADE"
            )
        )
        after = read_counts(connection)

    if any(after.values()):
        raise RuntimeError(f"Limpeza incompleta: {after}")

    print("Limpeza concluída com sucesso.")
    print("Dados restantes no PostgreSQL: categories=0, products=0, stock_movements=0")


if __name__ == "__main__":
    main()
