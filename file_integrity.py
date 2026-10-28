"""Content fingerprints for PDF evidence."""

from hashlib import sha256
from pathlib import Path


def sha256_arquivo(caminho):
    resumo = sha256()
    with Path(caminho).open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()
