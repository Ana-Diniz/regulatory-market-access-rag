"""Deterministic provenance checks for retrieved RAG evidence.

A located quote is not proof that the model interpreted it correctly.
"""

import re

CAMPOS = ("tecnologia_avaliada", "indicacao_clinica", "desfecho", "ano_relatorio", "ano_decisao")


def _normalizar(texto):
    return re.sub(r"\s+", " ", str(texto)).strip().casefold()


def _ocorrencia_delimitada(texto_procurado, texto_fonte):
    procurado = _normalizar(texto_procurado)
    return bool(procurado and re.search(
        rf"(?<!\w){re.escape(procurado)}(?!\w)",
        _normalizar(texto_fonte),
    ))


def _fonte_rastreavel(fonte):
    """A quote without a real document and positive PDF page is not auditable."""
    if not isinstance(fonte, dict):
        return False
    documento = fonte.get("documento")
    pagina = fonte.get("pagina")
    return (
        isinstance(documento, str)
        and bool(documento.strip())
        and documento.strip().casefold() != "desconhecido"
        and type(pagina) is int
        and pagina > 0
        and isinstance(fonte.get("texto"), str)
    )


def preparar_contexto(documentos):
    """Build a numbered context and an immutable-to-LLM source lookup."""
    blocos = []
    fontes = {}
    for indice, documento in enumerate(documentos, start=1):
        identificador = f"F{indice}"
        metadados = documento.metadata
        fontes[identificador] = {
            "documento": str(metadados.get("documento", "desconhecido")),
            "pagina": metadados.get("pagina"),
            "texto": documento.page_content,
        }
        # File paths stay in the local audit map, never in the LLM prompt.
        blocos.append(
            f"[{identificador}] Página: {fontes[identificador]['pagina']}\n{documento.page_content}"
        )
    return "\n\n".join(blocos), fontes


def auditar_extracao(extracao, fontes):
    """Return only fields with quotes located in a traceable source.

    For technology, clinical indication, and each year, the value must appear in the quote.
    Outcome interpretation still requires human review.
    """
    auditados = {}
    for campo in CAMPOS:
        dado = extracao.get(campo) or {}
        valor = dado.get("valor")
        identificador = dado.get("fonte_id")
        trecho = dado.get("trecho")
        fonte = fontes.get(identificador)

        if valor is None or (isinstance(valor, str) and not valor.strip()):
            status = "nao_encontrado"
        elif not _fonte_rastreavel(fonte) or not trecho or not str(trecho).strip():
            status = "sem_fonte_verificavel"
        elif not _ocorrencia_delimitada(trecho, fonte["texto"]):
            status = "trecho_nao_localizado"
        elif campo in ("tecnologia_avaliada", "indicacao_clinica", "ano_relatorio", "ano_decisao") and not _ocorrencia_delimitada(valor, trecho):
            status = "valor_nao_localizado_no_trecho"
        else:
            status = "trecho_localizado"

        localizado = status == "trecho_localizado"
        auditados[campo] = {
            "valor": valor if localizado else None,
            "status": status,
            "fonte": (
                {"id": identificador, "documento": fonte["documento"], "pagina": fonte["pagina"]}
                if localizado else None
            ),
            "trecho": trecho if localizado else None,
        }
    return auditados
