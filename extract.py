"""Retrieve regulatory evidence and extract fields with auditable citations."""
import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from build_db import COLLECTION, EMBEDDING_MODEL
from provenance import auditar_extracao, preparar_contexto
from schemas import DecisaoRegulatoria

QUERY = "RESUMO EXECUTIVO tecnologia indicação recomendação final incorporação SUS"
DEFAULT_MODEL = "qwen/qwen3.8-27b"


def buscar_contexto(pergunta=QUERY, pasta_db="chroma_db", k=6):
    if k < 1:
        raise ValueError("k deve ser maior que zero")
    if not Path(pasta_db).is_dir():
        raise FileNotFoundError(f"Banco vetorial não encontrado em {pasta_db}. Execute build_db.py.")

    embedding = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    banco = Chroma(
        collection_name=COLLECTION,
        persist_directory=str(pasta_db),
        embedding_function=embedding,
    )
    documentos = banco.similarity_search(pergunta, k=k)
    if not documentos:
        raise RuntimeError("Nenhuma evidência recuperada. Verifique se os PDFs foram indexados.")
    return documentos


def extrair_dados(pasta_db="chroma_db", k=6, modelo=None):
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        raise EnvironmentError("GROQ_API_KEY ausente. Configure a variável no ambiente ou no .env.")

    documentos = buscar_contexto(pasta_db=pasta_db, k=k)
    contexto, fontes = preparar_contexto(documentos)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Você é um analista de Market Access. Use somente as fontes fornecidas. "
         "Para cada campo, informe valor, fonte_id e um trecho LITERAL da fonte. "
         "Use null para valor, fonte_id e trecho quando não houver evidência suficiente. "
         "Desfecho: Favorável, Desfavorável ou Condicionado. "
         "O ano corresponde à publicação do relatório, não necessariamente à decisão final. "
         "Não invente páginas, citações ou valores."),
        ("user", "Fontes numeradas:\n{contexto}\n\nExtraia os campos solicitados."),
    ])
    llm = ChatGroq(model=modelo or os.getenv("GROQ_MODEL", DEFAULT_MODEL), temperature=0)
    resposta = (prompt | llm.with_structured_output(DecisaoRegulatoria)).invoke({"contexto": contexto})
    if resposta is None:
        raise RuntimeError("O modelo não retornou dados estruturados.")

    auditado = auditar_extracao(resposta.model_dump(), fontes)
    print(json.dumps(auditado, ensure_ascii=False, indent=2))
    return auditado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrai dados regulatórios com rastreabilidade por campo.")
    parser.add_argument("--db", default="chroma_db", help="Diretório do banco Chroma")
    parser.add_argument("--k", type=int, default=6, help="Quantidade de trechos recuperados")
    parser.add_argument("--model", default=None, help="Modelo disponível na conta Groq")
    args = parser.parse_args()
    extrair_dados(pasta_db=args.db, k=args.k, modelo=args.model)
