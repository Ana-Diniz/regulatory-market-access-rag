"""Index PDF reports in a local Chroma collection."""
import argparse
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from index_ids import agrupar_ids_por_documento, chunk_id, ids_obsoletos
from ingest import processar_pdf

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION = "regulatory_reports"


def encontrar_pdfs(origem):
    caminho = Path(origem)
    if caminho.is_dir():
        arquivos = sorted(
            (arquivo for arquivo in caminho.iterdir()
             if arquivo.is_file() and arquivo.suffix.lower() == ".pdf"),
            key=lambda arquivo: str(arquivo).casefold(),
        )
    elif caminho.is_file() and caminho.suffix.lower() == ".pdf":
        arquivos = [caminho]
    else:
        arquivos = []
    if not arquivos:
        raise FileNotFoundError(f"Nenhum PDF encontrado em: {caminho}")
    return sorted({arquivo.resolve() for arquivo in arquivos}, key=lambda arquivo: str(arquivo).casefold())


def criar_banco_vetorial(diretorio="data", pasta_db="chroma_db"):
    arquivos = encontrar_pdfs(diretorio)
    documentos = []
    ids = []
    ids_por_documento = {}

    for arquivo in arquivos:
        _, chunks = processar_pdf(str(arquivo))
        if not chunks:
            raise ValueError(
                f"PDF sem texto extraível: {arquivo}. "
                "PDFs digitalizados podem precisar de OCR."
            )
        ids_arquivo = []
        for indice, chunk in enumerate(chunks):
            documentos.append(Document(
                page_content=chunk["texto"],
                metadata=chunk["metadados"],
            ))
            identificador = chunk_id(arquivo, indice)
            ids.append(identificador)
            ids_arquivo.append(identificador)
        ids_por_documento[arquivo] = ids_arquivo

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    banco = Chroma(
        collection_name=COLLECTION,
        persist_directory=str(pasta_db),
        embedding_function=embeddings,
    )

    # Find old IDs even when earlier runs used relative instead of absolute paths.
    existentes = banco.get(include=["metadatas"])
    antigos = agrupar_ids_por_documento(
        existentes["ids"], existentes["metadatas"], ids_por_documento
    )
    # Upsert first: if embedding or persistence fails, do not remove old data.
    banco.add_documents(documentos, ids=ids)
    for caminho, atuais in ids_por_documento.items():
        obsoletos = ids_obsoletos(antigos[caminho], atuais)
        if obsoletos:
            banco.delete(ids=obsoletos)

    print(f"Indexados {len(documentos)} trechos de {len(arquivos)} arquivo(s) em {pasta_db}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexa PDFs locais para busca semântica.")
    parser.add_argument("--input", default="data", help="Diretório ou arquivo PDF")
    parser.add_argument("--db", default="chroma_db", help="Diretório do Chroma")
    args = parser.parse_args()
    criar_banco_vetorial(args.input, args.db)
