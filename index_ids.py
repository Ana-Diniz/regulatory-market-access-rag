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


def agrupar_ids_por_documento(ids, metadados, arquivos):
    """Find old chunk IDs even if a PDF was indexed with a different path spelling."""
    if len(ids) != len(metadados):
        raise ValueError("Índice retornou IDs e metadados em quantidades diferentes")

    encontrados = {Path(arquivo).resolve(): [] for arquivo in arquivos}
    for identificador, metadata in zip(ids, metadados):
        if not isinstance(metadata, dict):
            continue
        documento = metadata.get("documento")
        if not isinstance(documento, str) or not documento.strip():
            continue
        caminho = Path(documento).resolve()
        if caminho in encontrados:
            encontrados[caminho].append(identificador)
    return encontrados
