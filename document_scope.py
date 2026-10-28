"""Keep retrieval confined to one indexed report."""

from pathlib import Path
import re

from file_integrity import sha256_arquivo


def selecionar_documento(metadados, documento=None):
    if not metadados:
        raise RuntimeError("Banco sem metadados de PDFs indexados. Execute build_db.py.")
    if any(
        not isinstance(item, dict)
        or not isinstance(item.get("documento"), str)
        or not item["documento"].strip()
        for item in metadados
    ):
        raise RuntimeError("Índice contém trechos sem identificação de documento; reindexe os PDFs.")

    disponiveis = sorted({item["documento"] for item in metadados})
    if documento is None:
        if len(disponiveis) != 1:
            raise ValueError("Há vários PDFs indexados. Informe --document com o caminho de um PDF indexado.")
        return disponiveis[0]

    caminho = Path(documento).resolve()
    correspondencias = [item for item in disponiveis if Path(item).resolve() == caminho]
    if not correspondencias:
        raise ValueError(f"PDF não encontrado no índice: {documento}. Reindexe ou confira --document.")
    if len(correspondencias) > 1:
        raise RuntimeError("Índice contém caminhos equivalentes para o mesmo PDF; reindexe os documentos.")
    return correspondencias[0]



def validar_integridade_documento(metadados, selecionado):
    """Reject stale or inconsistent evidence when source fingerprints are available."""
    hashes = {
        item.get("sha256_pdf")
        for item in metadados
        if item["documento"] == selecionado
    }
    if hashes == {None}:
        return None  # Legacy indexes can still be queried until reindexed.

    if len(hashes) != 1:
        raise RuntimeError("Índice contém versões diferentes do mesmo PDF; reindexe o documento.")
    esperado = next(iter(hashes))
    if not isinstance(esperado, str) or re.fullmatch(r"[0-9a-f]{64}", esperado) is None:
        raise RuntimeError("Índice contém impressão digital inválida; reindexe o PDF.")

    try:
        atual = sha256_arquivo(selecionado)
    except OSError as erro:
        raise RuntimeError("PDF original indisponível para auditoria; restaure ou reindexe.") from erro
    if atual != esperado:
        raise RuntimeError("PDF original foi alterado desde a indexação; reindexe antes de extrair.")
    return esperado


def validar_integridade_evidencias(documentos):
    """Recheck the source PDF after the language model has processed its evidence."""
    metadados = [trecho.metadata for trecho in documentos]
    selecionado = selecionar_documento(metadados)
    return validar_integridade_documento(metadados, selecionado)


def recuperar_documentos(banco, pergunta, k=6, documento=None):
    if k < 1:
        raise ValueError("k deve ser maior que zero")
    metadados = banco.get(include=["metadatas"]).get("metadatas")
    selecionado = selecionar_documento(metadados, documento)
    hash_esperado = validar_integridade_documento(metadados, selecionado)
    documentos = banco.similarity_search(pergunta, k=k, filter={"documento": selecionado})
    if not documentos:
        raise RuntimeError("Nenhuma evidência recuperada para o PDF selecionado.")

    for trecho in documentos:
        metadata = getattr(trecho, "metadata", None)
        if not isinstance(metadata, dict) or metadata.get("documento") != selecionado:
            raise RuntimeError("Busca retornou evidência sem identificação do PDF selecionado; reindexe.")
        if hash_esperado is not None and metadata.get("sha256_pdf") != hash_esperado:
            raise RuntimeError("Busca retornou trecho de versão diferente do PDF; reindexe.")
        pagina = metadata.get("pagina")
        if type(pagina) is not int or pagina < 1:
            raise RuntimeError("Busca retornou evidência sem página válida; reindexe.")
        texto = getattr(trecho, "page_content", None)
        if not isinstance(texto, str) or not texto.strip():
            raise RuntimeError("Busca retornou evidência sem texto extraível; reindexe.")
    if hash_esperado is not None:
        try:
            hash_final = sha256_arquivo(selecionado)
        except OSError as erro:
            raise RuntimeError("PDF original indisponível durante a recuperação; reindexe.") from erro
        if hash_final != hash_esperado:
            raise RuntimeError("PDF original foi alterado durante a recuperação; reindexe.")
    return documentos
