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
    resultados = vector_db.similarity_search(pergunta, k=6)
    return resultados


# 4. Orquestração do RAG e Extração//Alteração na query_vetorial e prompt
def extrair_dados():
    # 1. A string de busca foca em encontrar as páginas onde o dado real está (o Resumo Executivo)
    query_vetorial = "RESUMO EXECUTIVO tecnologia indicação recomendação final incorporação SUS"
    
    # Busca os chunks no ChromaDB usando as palavras-chave
    documentos_recuperados = buscar_contexto(query_vetorial)
    contexto_junto = "\n\n".join([doc.page_content for doc in documentos_recuperados])

    print("Enviando contexto para o modelo processar via Groq...")
    
    llm = ChatGroq(model="qwen/qwen3.8-27b", temperature=0)
    llm_estruturado = llm.with_structured_output(DecisaoRegulatoria)

    # 2. O Prompt foca em dar a ordem rigorosa ao modelo
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Você é um analista de Market Access. Responda APENAS com base no contexto fornecido. Extraia o nome da tecnologia/medicamento, o ano da publicação do relatório e o desfecho da recomendação."),
        ("user", "Contexto encontrado no acervo:\n{contexto}\n\nPreencha os dados solicitados.")
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