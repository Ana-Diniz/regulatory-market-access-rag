from ingest import processar_pdf
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os

def criar_banco_vetorial():
    caminho_pdf = "data/Relatorio_Bedaquilina_TB_RR_MDR_XDR_546_2020_final.pdf"
    
    # 1. Puxa os textos extraídos do script anterior
    print("1. Processando o PDF...")
    _, chunks_brutos = processar_pdf(caminho_pdf)
    
    if not chunks_brutos:
        print("Erro: Nenhum chunk retornado. Verifique seu PDF.")
        return

    # 2. Converte nossos dicionários para o formato 'Document' do LangChain
    documentos = []
    for chunk in chunks_brutos:
        doc = Document(
            page_content=chunk["texto"],
            metadata=chunk["metadados"]
        )
        documentos.append(doc)

    print(f"2. {len(documentos)} blocos de texto preparados para vetorização.")

    # 3. Inicializa o modelo de embeddings (vai baixar um modelo leve de ~80MB na 1ª vez)
    print("3. Carregando modelo de embeddings (HuggingFace)...")
    modelo_embedding = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # 4. Cria o banco vetorial e salva no disco (pasta chroma_db)
    print("4. Vetorizando textos e salvando no ChromaDB. Isso pode levar um minutinho...")
    pasta_db = "./chroma_db"
    
    vector_db = Chroma.from_documents(
        documents=documentos,
        embedding=modelo_embedding,
        persist_directory=pasta_db
    )

    print(f"\n--- Sucesso! ---")
    print(f"Banco vetorial criado e salvo na pasta '{pasta_db}'.")
    print("Sua base de conhecimento estruturada já está pronta para receber perguntas!")

if __name__ == "__main__":
    criar_banco_vetorial()