"""Offline tests for document-scoped retrieval."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from document_scope import recuperar_documentos, selecionar_documento


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


if __name__ == "__main__":
    unittest.main()
