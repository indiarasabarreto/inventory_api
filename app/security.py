import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_DIR / ".env")

WAREHOUSE_PASSWORD = os.getenv("WAREHOUSE_PASSWORD")
SESSION_SECRET = os.getenv("SESSION_SECRET")

if not WAREHOUSE_PASSWORD or not SESSION_SECRET:
    raise RuntimeError(
        "WAREHOUSE_PASSWORD e SESSION_SECRET devem estar definidos no arquivo .env"
    )

def is_valid_password(password: str) -> bool:
    return secrets.compare_digest(password, WAREHOUSE_PASSWORD)