"""Stable, non-identifying chunk IDs for indexed PDFs.

A hash of the resolved source path avoids collisions between equally named
PDFs in different directories without exposing the path in the vector ID.
"""

from hashlib import sha256
from pathlib import Path


def chunk_id(caminho_pdf, indice):
    if not isinstance(indice, int) or isinstance(indice, bool) or indice < 0:
        raise ValueError("O índice do trecho deve ser um inteiro não negativo")
    caminho = Path(caminho_pdf).resolve()
    identificador = sha256(str(caminho).encode("utf-8")).hexdigest()
    return f"{identificador}:{indice}"


def ids_obsoletos(ids_existentes, ids_atuais):
    """Return IDs to delete only after the replacement upsert succeeds."""
    return sorted(set(ids_existentes) - set(ids_atuais))
