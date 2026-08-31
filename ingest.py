import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

def processar_pdf(caminho_pdf):
    print(f"Lendo o documento: {caminho_pdf}...")
    

    documento = pymupdf.open(caminho_pdf)
    textos_extraidos = []

    # 2. Extrai o texto página por página e guarda os metadados (página)
    for numero_pagina in range(len(documento)):
        pagina = documento.load_page(numero_pagina)
        texto = pagina.get_text()
        
        if texto.strip():
            textos_extraidos.append({
                "texto": texto,
                "metadados": {"documento": caminho_pdf, "pagina": numero_pagina + 1}
            })

    # 3. (Chunking)
    quebrador = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200, 
        length_function=len,
    )

    
    chunks_finais = []
    for item in textos_extraidos:
        pedacos = quebrador.split_text(item["texto"])
        for pedaco in pedacos:
            chunks_finais.append({
                "texto": pedaco,
                "metadados": item["metadados"]
            })

    return textos_extraidos, chunks_finais

# --- Execução do Script ---
if __name__ == "__main__":
    caminho_do_arquivo = "data/Relatorio_Bedaquilina_TB_RR_MDR_XDR_546_2020_final.pdf"
    
    paginas, chunks = processar_pdf(caminho_do_arquivo)
    
    print(f"\n--- Resumo da Extração ---")
    print(f"Total de páginas lidas: {len(paginas)}")
    print(f"Total de chunks gerados: {len(chunks)}")
    print("\n--- Exemplo do primeiro Chunk (Pedaço) gerado ---")
    print(chunks[0]['texto'])
    print(f"\nMetadados: {chunks[0]['metadados']}")