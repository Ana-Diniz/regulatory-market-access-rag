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
from document_scope import recuperar_documentos, validar_integridade_evidencias
from provenance import auditar_extracao, preparar_contexto
from schemas import DecisaoRegulatoria

QUERY = "RESUMO EXECUTIVO tecnologia indicação recomendação final incorporação SUS"
DEFAULT_MODEL = "qwen/qwen3.8-27b"
# Reserve headroom under providers with an output-token-per-minute quota of 1,000.
MAX_OUTPUT_TOKENS = 700


def buscar_contexto(pergunta=QUERY, pasta_db="chroma_db", k=6, documento=None):
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
    return recuperar_documentos(banco, pergunta, k=k, documento=documento)


def extrair_dados(pasta_db="chroma_db", k=6, modelo=None, documento=None,
                 pergunta=QUERY, max_output_tokens=MAX_OUTPUT_TOKENS):
    if max_output_tokens < 1:
        raise ValueError("max_output_tokens deve ser maior que zero")
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        raise EnvironmentError("GROQ_API_KEY ausente. Configure a variável no ambiente ou no .env.")

    documentos = buscar_contexto(pergunta=pergunta, pasta_db=pasta_db, k=k, documento=documento)
    contexto, fontes = preparar_contexto(documentos)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "Você é um analista de Market Access. Use somente as fontes fornecidas. "
         "Extraia cinco campos independentes, sempre com valor, fonte_id e trecho LITERAL curto. "
         "tecnologia_avaliada: apenas o nome do medicamento/tecnologia, sem indicação clínica. "
         "indicacao_clinica: população ou condição tratada; copie uma expressão exata da fonte, "
         "sem paráfrase, para permitir conferência textual. "
         "desfecho: Favorável, Desfavorável ou Condicionado; em recomendações condicionadas "
         "prefira Condicionado e cite a condição explícita. "
         "ano_relatorio: apenas o ano de publicação apresentado no relatório, por exemplo na capa. "
         "ano_decisao: apenas o ano de uma decisão/deliberação com data explícita, "
         "não deduza o ano da decisão a partir da capa ou do número do relatório. "
         "Para cada ano cite um trecho que contenha o ano e seu contexto. "
         "Use null para valor, fonte_id e trecho quando não houver evidência suficiente. "
         "Não invente páginas, citações ou valores e não use fontes diferentes das fornecidas."),
        ("user", "Fontes numeradas:\n{contexto}\n\nExtraia os campos solicitados."),
    ])
    llm = ChatGroq(
        model=modelo or os.getenv("GROQ_MODEL", DEFAULT_MODEL),
        temperature=0,
        max_tokens=max_output_tokens,
    )
    resposta = (prompt | llm.with_structured_output(DecisaoRegulatoria)).invoke({"contexto": contexto})
    if resposta is None:
        raise RuntimeError("O modelo não retornou dados estruturados.")

    validar_integridade_evidencias(documentos)
    auditado = auditar_extracao(resposta.model_dump(), fontes)
    print(json.dumps(auditado, ensure_ascii=False, indent=2))
    return auditado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrai dados regulatórios com rastreabilidade por campo.")
    parser.add_argument("--db", default="chroma_db", help="Diretório do banco Chroma")
    parser.add_argument("--k", type=int, default=6, help="Quantidade de trechos recuperados")
    parser.add_argument("--model", default=None, help="Modelo disponível na conta Groq")
    parser.add_argument("--document", default=None, help="Caminho do PDF indexado a consultar")
    parser.add_argument("--query", default=QUERY, help="Consulta usada para recuperar evidências")
    parser.add_argument("--max-output-tokens", type=int, default=MAX_OUTPUT_TOKENS,
                        help="Limite de tokens de saída da Groq (padrão: 700)")
    args = parser.parse_args()
    extrair_dados(pasta_db=args.db, k=args.k, modelo=args.model,
                 documento=args.document, pergunta=args.query,
                 max_output_tokens=args.max_output_tokens)
