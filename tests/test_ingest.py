"""Integration tests using tiny synthetic PDFs; no external services."""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import pymupdf

from ingest import main, processar_pdf


class IngestTests(unittest.TestCase):
    def test_page_metadata_skips_blank_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "relatorio.pdf"
            with pymupdf.open() as pdf:
                pdf.new_page()
                pagina = pdf.new_page()
                pagina.insert_text((72, 72), "Tecnologia bedaquilina em 2020.")
                pdf.save(str(caminho))

            paginas, chunks = processar_pdf(caminho)
            self.assertEqual(len(paginas), 1)
            self.assertEqual(paginas[0]["metadados"]["pagina"], 2)
            self.assertEqual(paginas[0]["metadados"]["documento"], str(caminho.resolve()))
            self.assertTrue(chunks)
            self.assertTrue(all(c["metadados"]["pagina"] == 2 for c in chunks))
            self.assertIn("bedaquilina", chunks[0]["texto"])

    def test_empty_pdf_returns_no_chunks_without_index_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "vazio.pdf"
            with pymupdf.open() as pdf:
                pdf.new_page()
                pdf.save(str(caminho))

            self.assertEqual(processar_pdf(caminho), ([], []))
            saida = io.StringIO()
            with redirect_stdout(saida):
                codigo = main(["--input", str(caminho)])
            self.assertEqual(codigo, 1)
            self.assertIn("Nenhum trecho", saida.getvalue())

    def test_missing_and_non_pdf_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                processar_pdf(Path(tmp) / "ausente.pdf")
            caminho = Path(tmp) / "relatorio.txt"
            caminho.write_text("texto", encoding="utf-8")
            with self.assertRaises(ValueError):
                processar_pdf(caminho)

    def test_document_is_closed_if_page_extraction_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            caminho = Path(tmp) / "quebrado.pdf"
            caminho.write_bytes(b"test fixture")
            with patch("ingest.pymupdf.open") as abrir:
                documento = abrir.return_value.__enter__.return_value
                documento.__len__.return_value = 1
                documento.load_page.side_effect = RuntimeError("falha de leitura")
                with self.assertRaisesRegex(RuntimeError, "falha de leitura"):
                    processar_pdf(caminho)
                abrir.return_value.__exit__.assert_called_once()


if __name__ == "__main__":
    unittest.main()
