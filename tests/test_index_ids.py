"""Offline regression tests for stable IDs and safe reindex cleanup."""
import tempfile
import unittest
from pathlib import Path

from index_ids import chunk_id, ids_obsoletos


class IndexIdsTests(unittest.TestCase):
    def test_same_source_and_index_produce_same_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / "report.pdf"
            self.assertEqual(chunk_id(pdf, 0), chunk_id(pdf, 0))
            self.assertNotEqual(chunk_id(pdf, 0), chunk_id(pdf, 1))

    def test_same_filename_in_different_directories_does_not_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a" / "report.pdf"
            b = Path(tmp) / "b" / "report.pdf"
            self.assertNotEqual(chunk_id(a, 0), chunk_id(b, 0))

    def test_invalid_chunk_index_is_rejected(self):
        for index in (-1, True, "1", 1.5):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    chunk_id("report.pdf", index)

    def test_stale_ids_include_old_scheme_and_shrunken_chunks(self):
        atuais = [chunk_id("report.pdf", 0), chunk_id("report.pdf", 1)]
        existentes = ["report.pdf:0", *atuais, chunk_id("report.pdf", 2)]
        self.assertEqual(
            ids_obsoletos(existentes, atuais),
            sorted(["report.pdf:0", chunk_id("report.pdf", 2)]),
        )

    def test_no_deletion_when_all_existing_ids_are_current(self):
        atuais = [chunk_id("report.pdf", 0)]
        self.assertEqual(ids_obsoletos(atuais, atuais), [])


if __name__ == "__main__":
    unittest.main()
