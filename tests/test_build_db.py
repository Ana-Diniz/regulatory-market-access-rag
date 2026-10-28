"""Offline tests for PDF integrity across vector indexing operations."""

import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from file_integrity import sha256_arquivo


class FakeDocument:
    def __init__(self, page_content, metadata):
        self.page_content = page_content
        self.metadata = metadata


def carregar_indexador():
    modulos = {}
    for nome in ("langchain_chroma", "langchain_core", "langchain_core.documents",
                 "langchain_huggingface", "ingest"):
        modulos[nome] = types.ModuleType(nome)
    modulos["langchain_chroma"].Chroma = Mock()
    modulos["langchain_core.documents"].Document = FakeDocument
    modulos["langchain_huggingface"].HuggingFaceEmbeddings = Mock()
    modulos["ingest"].processar_pdf = Mock()
    caminho = Path(__file__).resolve().parents[1] / "build_db.py"
    spec = importlib.util.spec_from_file_location("_build_db_integrity_test", caminho)
    modulo = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modulos):
        spec.loader.exec_module(modulo)
    return modulo


indexador = carregar_indexador()


class BuildDbIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.pdf = Path(self.pasta.name) / "report.pdf"
        self.pdf.write_bytes(b"original PDF")
        self.banco = Mock()
        self.banco.get.return_value = {"ids": [], "metadatas": []}
        self.chroma = patch.object(indexador, "Chroma", return_value=self.banco)
        self.embeddings = patch.object(indexador, "HuggingFaceEmbeddings", return_value=object())
        self.encontrar = patch.object(indexador, "encontrar_pdfs", return_value=[self.pdf])
        self.processar = patch.object(indexador, "processar_pdf", return_value=(
            [],
            [{"texto": "Recomendacao de 2020.", "metadados": {
                "documento": str(self.pdf),
                "pagina": 1,
                "sha256_pdf": sha256_arquivo(self.pdf),
            }}],
        ))
        for mocker in (self.chroma, self.embeddings, self.encontrar, self.processar):
            mocker.start()
            self.addCleanup(mocker.stop)

    def test_pdf_estavel_e_indexado(self):
        indexador.criar_banco_vetorial(self.pdf, self.pasta.name)
        self.banco.add_documents.assert_called_once()
        self.banco.delete.assert_not_called()

    def test_pdf_alterado_ao_carregar_embeddings_nao_e_indexado(self):
        def alterar_ao_carregar(**kwargs):
            self.pdf.write_bytes(b"changed while embeddings load")
            return object()

        with patch.object(indexador, "HuggingFaceEmbeddings", side_effect=alterar_ao_carregar):
            with self.assertRaisesRegex(RuntimeError, "alterado durante a indexação"):
                indexador.criar_banco_vetorial(self.pdf, self.pasta.name)
        self.banco.add_documents.assert_not_called()

    def test_pdf_alterado_durante_upsert_nao_remove_trechos_antigos(self):
        self.banco.get.return_value = {
            "ids": ["legacy:0"],
            "metadatas": [{"documento": str(self.pdf)}],
        }
        self.banco.add_documents.side_effect = lambda *args, **kwargs: self.pdf.write_bytes(
            b"changed during upsert"
        )
        with self.assertRaisesRegex(RuntimeError, "alterado durante a indexação"):
            indexador.criar_banco_vetorial(self.pdf, self.pasta.name)
        self.banco.delete.assert_not_called()

    def test_pdf_removido_durante_upsert_nao_remove_trechos_antigos(self):
        self.banco.get.return_value = {
            "ids": ["legacy:0"],
            "metadatas": [{"documento": str(self.pdf)}],
        }
        self.banco.add_documents.side_effect = lambda *args, **kwargs: self.pdf.unlink()
        with self.assertRaisesRegex(RuntimeError, "indisponível durante a indexação"):
            indexador.criar_banco_vetorial(self.pdf, self.pasta.name)
        self.banco.delete.assert_not_called()

    def test_reindexacao_estavel_remove_ids_obsoletos(self):
        self.banco.get.return_value = {
            "ids": ["legacy:0"],
            "metadatas": [{"documento": str(self.pdf)}],
        }
        indexador.criar_banco_vetorial(self.pdf, self.pasta.name)
        self.banco.delete.assert_called_once_with(ids=["legacy:0"])


if __name__ == "__main__":
    unittest.main()
