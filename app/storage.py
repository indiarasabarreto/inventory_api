"""
Gerenciamento de arquivos importados.

Em produção (SUPABASE_URL + SUPABASE_SERVICE_KEY definidos):
    usa Supabase Storage.

Em desenvolvimento (SQLite / sem variáveis de storage):
    salva em app/uploads/ localmente.
"""

import os
import httpx
from pathlib import Path

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "importacoes")

_LOCAL_UPLOAD_DIR = Path(__file__).parent / "uploads"


def _use_supabase() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY,
    }


def upload_file(stored_name: str, content: bytes) -> None:
    """Salva o arquivo no Supabase Storage (produção) ou em disco (local)."""
    if _use_supabase():
        url = (
            f"{SUPABASE_URL}/storage/v1/object/"
            f"{SUPABASE_STORAGE_BUCKET}/{stored_name}"
        )
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                content=content,
                headers={
                    **_headers(),
                    "Content-Type": "application/octet-stream",
                    "x-upsert": "true",
                },
            )
            response.raise_for_status()
    else:
        _LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        (_LOCAL_UPLOAD_DIR / stored_name).write_bytes(content)


def delete_file(stored_name: str) -> None:
    """Remove o arquivo do Supabase Storage (produção) ou do disco (local).
    Não falha se o arquivo não existir."""
    if _use_supabase():
        url = (
            f"{SUPABASE_URL}/storage/v1/object/"
            f"{SUPABASE_STORAGE_BUCKET}"
        )
        with httpx.Client(timeout=30.0) as client:
            response = client.delete(
                url,
                json={"prefixes": [stored_name]},
                headers={
                    **_headers(),
                    "Content-Type": "application/json",
                },
            )
            # Supabase ignora prefixos inexistentes; 404 genérico é aceitável.
            if response.status_code not in (200, 404):
                response.raise_for_status()
    else:
        local_path = _LOCAL_UPLOAD_DIR / stored_name
        if local_path.exists():
            local_path.unlink()