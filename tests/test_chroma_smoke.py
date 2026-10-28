"""Offline Chroma integration smoke test with real PDFs and deterministic embeddings."""

import tempfile
import unittest
from pathlib import Path

import pymupdf

from document_scope import recuperar_documentos
from index_ids import chunk_id
from ingest import processar_pdf
from provenance import auditar_extracao, preparar_contexto

try:
    import chromadb
    from langchain_chroma import Chroma
    from langchain_core.documents import Document
except ImportError:
    Chroma = None


class DeterministicEmbeddings:
    """Local embeddings for wiring tests; not a semantic-quality benchmark."""

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        normalizado = text.casefold()
        return [
            1.0 + float("bedaquilina" in normalizado),
            1.0 + float("trastuzumabe" in normalizado),
            1.0 + float("recomend" in normalizado),
        ]


@unittest.skipUnless(Chroma is not None, "langchain-chroma não instalado")
class ChromaSmokeTests(unittest.TestCase):
    def test_pdf_ingestion_index_retrieval_and_evidence_audit(self):
        with tempfile.TemporaryDirectory() as pasta, chromadb.PersistentClient(
            path=str(Path(pasta) / "db")
        ) as client:
            raiz = Path(pasta)
            banco = Chroma(
                collection_name="regulatory_smoke",
                client=client,
                embedding_function=DeterministicEmbeddings(),
            )
            fontes = [
                ("bedaquilina.pdf", "Bedaquilina. Recomendacao condicionada. Ano 2020."),
                ("trastuzumabe.pdf", "Trastuzumabe. Recomendacao favoravel. Ano 2022."),
            ]
            documentos = []
            ids = []
            caminhos = []

            for nome, texto in fontes:
                caminho = raiz / nome
                with pymupdf.open() as pdf:
                    pagina = pdf.new_page()
                    pagina.insert_text((72, 72), texto)
                    pdf.save(str(caminho))
                caminhos.append(caminho)
                paginas, chunks = processar_pdf(caminho)
                self.assertEqual(len(paginas), 1)
                self.assertTrue(chunks)
                for indice, chunk in enumerate(chunks):
                    documentos.append(Document(
                        page_content=chunk["texto"],
                        metadata=chunk["metadados"],
                    ))
                    ids.append(chunk_id(caminho, indice))

            banco.add_documents(documentos, ids=ids)
            recuperados = recuperar_documentos(
                banco, "bedaquilina", k=5, documento=str(caminhos[0])
            )
            self.assertTrue(recuperados)
            self.assertTrue(all(
                trecho.metadata["documento"] == str(caminhos[0])
                for trecho in recuperados
            ))
            self.assertTrue(all(
                "Trastuzumabe" not in trecho.page_content
                for trecho in recuperados
            ))

            contexto, mapa = preparar_contexto(recuperados)
            self.assertIn("Bedaquilina", contexto)
            resultado = auditar_extracao({
                "tecnologia_avaliada": {
                    "valor": "Bedaquilina",
                    "fonte_id": "F1",
                    "trecho": "Bedaquilina",
                },
                "desfecho": {
                    "valor": "Condicionado",
                    "fonte_id": "F1",
                    "trecho": "Recomendacao condicionada",
                },
                "ano_decisao": {
                    "valor": 2020,
                    "fonte_id": "F1",
                    "trecho": "Ano 2020",
                },
            }, mapa)
            self.assertTrue(all(
                campo["status"] == "trecho_localizado"
                for campo in resultado.values()
            ))

            caminhos[0].write_bytes(b"PDF modificado")
            with self.assertRaisesRegex(RuntimeError, "alterado"):
                recuperar_documentos(
                    banco, "bedaquilina", documento=str(caminhos[0])
                )


if __name__ == "__main__":
    unittest.main()
