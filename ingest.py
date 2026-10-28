"""Extract page-aware text chunks from a PDF and close the document safely."""

import argparse
from pathlib import Path

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter


def processar_pdf(caminho_pdf):
    caminho = Path(caminho_pdf)
    if not caminho.is_file():
        raise FileNotFoundError(f"PDF não encontrado: {caminho}")
    if caminho.suffix.lower() != ".pdf":
        raise ValueError(f"O arquivo informado não é um PDF: {caminho}")

    print(f"Lendo o documento: {caminho}...")
    textos_extraidos = []
    # Closing the PDF also when extraction fails avoids leaked file handles.
    with pymupdf.open(str(caminho)) as documento:
        for numero_pagina in range(len(documento)):
            texto = documento.load_page(numero_pagina).get_text()
            if texto.strip():
                textos_extraidos.append({
                    "texto": texto,
                    "metadados": {
                        "documento": str(caminho.resolve()),
                        "pagina": numero_pagina + 1,
                    },
                })

    quebrador = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    chunks_finais = []
    for item in textos_extraidos:
        for pedaco in quebrador.split_text(item["texto"]):
            chunks_finais.append({
                "texto": pedaco,
                "metadados": item["metadados"],
            })
    return textos_extraidos, chunks_finais


def main(argv=None):
    parser = argparse.ArgumentParser(description="Inspeciona o texto extraído de um PDF.")
    parser.add_argument("--input", required=True, help="Caminho para um arquivo PDF")
    args = parser.parse_args(argv)

    paginas, chunks = processar_pdf(args.input)
    print(f"Total de páginas com texto: {len(paginas)}")
    print(f"Total de chunks gerados: {len(chunks)}")
    if not chunks:
        print("Nenhum trecho de texto extraível encontrado; o PDF pode precisar de OCR.")
        return 1

    print("\n--- Exemplo do primeiro chunk ---")
    print(chunks[0]["texto"])
    print(f"Metadados: {chunks[0]['metadados']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
