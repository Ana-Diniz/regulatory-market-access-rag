import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

# 1. Carrega a chave da API do arquivo .env
load_dotenv()

# 2. Define o Schema de Dados (A estrutura que queremos forçar o modelo a preencher)
class DecisaoRegulatoria(BaseModel):
    tecnologia_avaliada: str = Field(description="Nome exato do medicamento ou tecnologia avaliada no relatório")
    desfecho: str = Field(description="O desfecho da recomendação: Favorável, Desfavorável, ou Condicionado")
    ano_decisao: str = Field(description="O ano em que o relatório de recomendação foi publicado")

# 3. Função para buscar no Banco Vetorial
def buscar_contexto(pergunta):
    print("Buscando evidências no banco vetorial local...")
    modelo_embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(persist_directory="./chroma_db", embedding_function=modelo_embedding)
    
    # Recupera os 4 trechos mais relevantes do PDF
    resultados = vector_db.similarity_search(pergunta, k=4)
    return resultados

# 4. Orquestração do RAG e Extração
def extrair_dados():
    pergunta = "Qual medicamento está sendo avaliado neste relatório, de que ano é o documento, e qual foi a recomendação final de incorporação (desfecho)?"
    
    # Busca os chunks no ChromaDB
    documentos_recuperados = buscar_contexto(pergunta)
    contexto_junto = "\n\n".join([doc.page_content for doc in documentos_recuperados])

    print("Enviando contexto para o modelo Llama-3 processar via Groq...")
    
    # Inicializa o modelo rápido da Groq
    llm = ChatGroq(model="qwen/qwen3.8-27b", temperature=0)
    # Força o modelo a respeitar nosso Schema Pydantic
    llm_estruturado = llm.with_structured_output(DecisaoRegulatoria)

    # Cria o Prompt rigoroso contra alucinações
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Você é um analista de regulação de saúde (Market Access). Responda APENAS com base no contexto fornecido. Extraia as informações solicitadas com precisão e brevidade."),
        ("user", "Contexto encontrado no acervo:\n{contexto}\n\nExtraia as informações solicitadas.")
    ])

    # Conecta o prompt com o modelo estruturado
    chain = prompt | llm_estruturado

    # Executa a extração
    resultado = chain.invoke({"contexto": contexto_junto})

    print("\n" + "="*40)
    print("      RESULTADO DA ESTRUTURAÇÃO")
    print("="*40)
    print(f"Tecnologia Avaliada: {resultado.tecnologia_avaliada}")
    print(f"Ano da Decisão: {resultado.ano_decisao}")
    print(f"Desfecho: {resultado.desfecho}")
    
    print("\n--- Rastreabilidade (Fontes Utilizadas) ---")
    for i, doc in enumerate(documentos_recuperados):
         print(f"- Evidência extraída da Página: {doc.metadata.get('pagina', 'N/A')}")

if __name__ == "__main__":
    extrair_dados()