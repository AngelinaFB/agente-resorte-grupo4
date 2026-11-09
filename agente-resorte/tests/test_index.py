import tempfile
import unittest
from pathlib import Path

from chatbot.index import build_index, search, stats, verify_index


def sample_data():
    documents = [
        {
            "doc_id": "doc-1",
            "source_path": "Bibliografía/demo.pdf",
            "source_type": "bibliografia",
            "origin": "pdf",
            "title": "demo",
            "sha256": "abc",
            "pdf_pages": 2,
            "text_pages": 2,
            "char_count": 120,
            "needs_ocr_pages": 0,
            "flagged_pages": 0,
            "chunk_count": 2,
        }
    ]
    pages = [
        {
            "doc_id": "doc-1",
            "page": 1,
            "text": "La energia mecanica se conserva en un campo conservativo.",
            "char_count": 60,
            "word_count": 9,
            "needs_ocr": False,
            "quality_flags": [],
        },
        {
            "doc_id": "doc-1",
            "page": 2,
            "text": "El trabajo de la fuerza neta es igual a la variacion de energia.",
            "char_count": 60,
            "word_count": 11,
            "needs_ocr": False,
            "quality_flags": [],
        },
    ]
    chunks = [
        {
            "chunk_id": "doc-1:p1:c0",
            "doc_id": "doc-1",
            "page": 1,
            "chunk_index": 0,
            "text": pages[0]["text"],
            "word_count": pages[0]["word_count"],
            "char_count": pages[0]["char_count"],
        },
        {
            "chunk_id": "doc-1:p2:c0",
            "doc_id": "doc-1",
            "page": 2,
            "chunk_index": 0,
            "text": pages[1]["text"],
            "word_count": pages[1]["word_count"],
            "char_count": pages[1]["char_count"],
        },
    ]
    return documents, pages, chunks


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "index.sqlite"
        docs, pages, chunks = sample_data()
        build_index(self.db, docs, pages, chunks)

    def tearDown(self):
        self.tmp.cleanup()

    def test_search_without_accent(self):
        results = search("energia", db_path=self.db, limit=5)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["doc_id"], "doc-1")
        self.assertIn("chunk_id", results[0])
        self.assertIn("needs_ocr", results[0])
        self.assertIn("quality_flags", results[0])
        self.assertIn("snippet", results[0])

    def test_search_filter_page(self):
        results = search("energia", db_path=self.db, page=2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["page"], 2)

    def test_stats(self):
        data = stats(self.db)
        self.assertEqual(data["documents"], 1)
        self.assertEqual(data["pdf_pages"], 2)
        self.assertEqual(data["chunks"], 2)
        self.assertEqual(data["fts_rows"], 2)

    def test_verify(self):
        data = verify_index(self.db)
        self.assertTrue(data["ok"], data["errors"])
        self.assertEqual(data["checks"]["counts"]["chunks"], 2)

    def test_search_empty_query(self):
        self.assertEqual(search("   ", db_path=self.db), [])


if __name__ == "__main__":
    unittest.main()
