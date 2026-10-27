"""Keep retrieval confined to one indexed report."""

from pathlib import Path


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


def recuperar_documentos(banco, pergunta, k=6, documento=None):
    if k < 1:
        raise ValueError("k deve ser maior que zero")
    metadados = banco.get(include=["metadatas"]).get("metadatas")
    selecionado = selecionar_documento(metadados, documento)
    documentos = banco.similarity_search(pergunta, k=k, filter={"documento": selecionado})
    if not documentos:
        raise RuntimeError("Nenhuma evidência recuperada para o PDF selecionado.")
    return documentos
