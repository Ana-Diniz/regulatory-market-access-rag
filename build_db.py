"""Index PDF reports in a local Chroma collection."""
import argparse
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from ingest import processar_pdf

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION = "regulatory_reports"


def criar_banco_vetorial(diretorio="data", pasta_db="chroma_db"):
    origem = Path(diretorio)
    arquivos = sorted(origem.glob("*.pdf")) if origem.is_dir() else ([origem] if origem.is_file() else [])
    if not arquivos:
        raise FileNotFoundError(f"Nenhum PDF encontrado em: {origem}")

    documentos = []
    ids = []
    for arquivo in arquivos:
        _, chunks = processar_pdf(str(arquivo))
        for indice, chunk in enumerate(chunks):
            documentos.append(Document(page_content=chunk["texto"], metadata=chunk["metadados"]))
            ids.append(f"{arquivo.name}:{indice}")

    if not documentos:
        raise ValueError("Os PDFs não possuem texto extraível; PDFs digitalizados podem precisar de OCR.")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    banco = Chroma(
        collection_name=COLLECTION,
        persist_directory=str(pasta_db),
        embedding_function=embeddings,
    )
    # Upsert keeps repeated indexing idempotent instead of duplicating chunks.
    banco.add_documents(documentos, ids=ids)
    print(f"Indexados {len(documentos)} trechos de {len(arquivos)} arquivo(s) em {pasta_db}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Indexa PDFs locais para busca semântica.")
    parser.add_argument("--input", default="data", help="Diretório ou arquivo PDF")
    parser.add_argument("--db", default="chroma_db", help="Diretório do Chroma")
    args = parser.parse_args()
    criar_banco_vetorial(args.input, args.db)
