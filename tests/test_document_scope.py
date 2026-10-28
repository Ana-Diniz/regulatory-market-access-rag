"""Offline tests for document-scoped retrieval."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from document_scope import recuperar_documentos, selecionar_documento, validar_integridade_evidencias
from file_integrity import sha256_arquivo


class DocumentScopeTests(unittest.TestCase):
    def test_single_document_is_selected_automatically(self):
        self.assertEqual(
            selecionar_documento([{"documento": "a.pdf"}, {"documento": "a.pdf"}]),
            "a.pdf",
        )

    def test_multiple_documents_require_explicit_selection(self):
        with self.assertRaisesRegex(ValueError, "--document"):
            selecionar_documento([{"documento": "a.pdf"}, {"documento": "b.pdf"}])

    def test_selected_document_filters_vector_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            selected = str(Path(tmp) / "b.pdf")
            banco = Mock()
            banco.get.return_value = {
                "metadatas": [
                    {"documento": str(Path(tmp) / "a.pdf")},
                    {"documento": selected},
                ],
            }
            trecho = SimpleNamespace(
                metadata={"documento": selected, "pagina": 2},
                page_content="Recomendação do relatório.",
            )
            banco.similarity_search.return_value = [trecho]
            self.assertEqual(
                recuperar_documentos(banco, "question", k=4, documento=selected),
                [trecho],
            )
            banco.get.assert_called_once_with(include=["metadatas"])
            banco.similarity_search.assert_called_once_with(
                "question", k=4, filter={"documento": selected}
            )

    def test_unknown_document_is_rejected_without_search(self):
        banco = Mock()
        banco.get.return_value = {"metadatas": [{"documento": "a.pdf"}]}
        with self.assertRaisesRegex(ValueError, "não encontrado"):
            recuperar_documentos(banco, "question", documento="b.pdf")
        banco.similarity_search.assert_not_called()

    def test_missing_document_metadata_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "sem identificação"):
            selecionar_documento([{"pagina": 2}, {"documento": "a.pdf"}])

    def test_empty_results_are_rejected(self):
        banco = Mock()
        banco.get.return_value = {"metadatas": [{"documento": "a.pdf"}]}
        banco.similarity_search.return_value = []
        with self.assertRaisesRegex(RuntimeError, "Nenhuma evidência"):
            recuperar_documentos(banco, "question")

    def test_retrieval_rejects_foreign_document_even_if_backend_returns_it(self):
        banco = Mock()
        banco.get.return_value = {"metadatas": [{"documento": "a.pdf"}, {"documento": "b.pdf"}]}
        banco.similarity_search.return_value = [
            SimpleNamespace(metadata={"documento": "b.pdf", "pagina": 3}, page_content="Outra fonte")
        ]
        with self.assertRaisesRegex(RuntimeError, "PDF selecionado"):
            recuperar_documentos(banco, "question", documento="a.pdf")

    def test_retrieval_rejects_missing_or_invalid_page(self):
        banco = Mock()
        banco.get.return_value = {"metadatas": [{"documento": "a.pdf"}]}
        for pagina in (None, 0, "3", True):
            with self.subTest(pagina=pagina):
                banco.similarity_search.return_value = [
                    SimpleNamespace(metadata={"documento": "a.pdf", "pagina": pagina}, page_content="Texto")
                ]
                with self.assertRaisesRegex(RuntimeError, "página válida"):
                    recuperar_documentos(banco, "question")

    def test_retrieval_rejects_empty_text(self):
        banco = Mock()
        banco.get.return_value = {"metadatas": [{"documento": "a.pdf"}]}
        banco.similarity_search.return_value = [
            SimpleNamespace(metadata={"documento": "a.pdf", "pagina": 1}, page_content="   ")
        ]
        with self.assertRaisesRegex(RuntimeError, "sem texto"):
            recuperar_documentos(banco, "question")

    def test_modified_pdf_is_rejected_before_vector_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "report.pdf"
            caminho.write_bytes(b"first version")
            esperado = sha256_arquivo(caminho)
            banco = Mock()
            banco.get.return_value = {
                "metadatas": [{"documento": str(caminho), "sha256_pdf": esperado}]
            }
            caminho.write_bytes(b"second version")
            with self.assertRaisesRegex(RuntimeError, "alterado"):
                recuperar_documentos(banco, "question")
            banco.similarity_search.assert_not_called()

    def test_missing_pdf_is_rejected_before_vector_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "report.pdf"
            caminho.write_bytes(b"indexed")
            banco = Mock()
            banco.get.return_value = {
                "metadatas": [{"documento": str(caminho), "sha256_pdf": sha256_arquivo(caminho)}]
            }
            caminho.unlink()
            with self.assertRaisesRegex(RuntimeError, "indisponível"):
                recuperar_documentos(banco, "question")
            banco.similarity_search.assert_not_called()

    def test_inconsistent_or_malformed_fingerprints_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "report.pdf"
            caminho.write_bytes(b"source")
            correto = sha256_arquivo(caminho)
            banco = Mock()
            for hashes in ([correto, None], ["invalid"]):
                with self.subTest(hashes=hashes):
                    banco.get.return_value = {
                        "metadatas": [
                            {"documento": str(caminho), "sha256_pdf": hash_valor}
                            for hash_valor in hashes
                        ]
                    }
                    with self.assertRaisesRegex(RuntimeError, "reindexe"):
                        recuperar_documentos(banco, "question")
            banco.similarity_search.assert_not_called()

    def test_pdf_modified_during_vector_search_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "report.pdf"
            caminho.write_bytes(b"indexed PDF")
            esperado = sha256_arquivo(caminho)
            banco = Mock()
            banco.get.return_value = {
                "metadatas": [{"documento": str(caminho), "sha256_pdf": esperado}]
            }
            trecho = SimpleNamespace(
                metadata={"documento": str(caminho), "pagina": 1, "sha256_pdf": esperado},
                page_content="Recomendacao do relatorio.",
            )

            def alterar_durante_busca(*args, **kwargs):
                caminho.write_bytes(b"changed PDF")
                return [trecho]

            banco.similarity_search.side_effect = alterar_durante_busca
            with self.assertRaisesRegex(RuntimeError, "alterado durante a recuperação"):
                recuperar_documentos(banco, "question")

    def test_pdf_removed_during_vector_search_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "report.pdf"
            caminho.write_bytes(b"indexed PDF")
            esperado = sha256_arquivo(caminho)
            banco = Mock()
            banco.get.return_value = {
                "metadatas": [{"documento": str(caminho), "sha256_pdf": esperado}]
            }
            trecho = SimpleNamespace(
                metadata={"documento": str(caminho), "pagina": 1, "sha256_pdf": esperado},
                page_content="Recomendacao do relatorio.",
            )

            def remover_durante_busca(*args, **kwargs):
                caminho.unlink()
                return [trecho]

            banco.similarity_search.side_effect = remover_durante_busca
            with self.assertRaisesRegex(RuntimeError, "indisponível durante a recuperação"):
                recuperar_documentos(banco, "question")

    def test_post_inference_integrity_rejects_changed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "report.pdf"
            caminho.write_bytes(b"indexed version")
            esperado = sha256_arquivo(caminho)
            trecho = SimpleNamespace(metadata={
                "documento": str(caminho),
                "pagina": 1,
                "sha256_pdf": esperado,
            }, page_content="Evidencia original.")

            self.assertEqual(validar_integridade_evidencias([trecho]), esperado)
            caminho.write_bytes(b"modified while model was running")
            with self.assertRaisesRegex(RuntimeError, "alterado"):
                validar_integridade_evidencias([trecho])

    def test_post_inference_integrity_rejects_missing_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "report.pdf"
            caminho.write_bytes(b"indexed version")
            trecho = SimpleNamespace(metadata={
                "documento": str(caminho),
                "pagina": 1,
                "sha256_pdf": sha256_arquivo(caminho),
            }, page_content="Evidencia original.")
            caminho.unlink()
            with self.assertRaisesRegex(RuntimeError, "indisponível"):
                validar_integridade_evidencias([trecho])

    def test_matching_fingerprint_allows_retrieval_but_rejects_wrong_chunk_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "report.pdf"
            caminho.write_bytes(b"original PDF")
            correto = sha256_arquivo(caminho)
            banco = Mock()
            banco.get.return_value = {
                "metadatas": [{"documento": str(caminho), "sha256_pdf": correto}]
            }
            metadata = {"documento": str(caminho), "pagina": 1, "sha256_pdf": correto}
            trecho = SimpleNamespace(metadata=metadata, page_content="Texto regulatório.")
            banco.similarity_search.return_value = [trecho]
            self.assertEqual(recuperar_documentos(banco, "question"), [trecho])

            trecho.metadata = {**metadata, "sha256_pdf": "0" * 64}
            with self.assertRaisesRegex(RuntimeError, "versão diferente"):
                recuperar_documentos(banco, "question")


if __name__ == "__main__":
    unittest.main()
