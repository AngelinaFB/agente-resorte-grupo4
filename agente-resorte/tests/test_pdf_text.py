import unittest
from pathlib import Path

from chatbot import config
from chatbot.ingest import _chunk_page, _page_quality
from chatbot.pdf_text import extract_pdf


class PdfTextTests(unittest.TestCase):
    def test_coordenadas_extracts_text(self):
        path = config.BIBLIOGRAFIA_DIR / "coordenadas intrinsecas y polares.pdf"
        if not path.exists():
            self.skipTest("No esta el PDF de coordenadas")
        pages = extract_pdf(path)
        self.assertEqual(len(pages), 6)
        self.assertGreater(sum(p.char_count for p in pages), 40000)
        self.assertIn("coordenadas", pages[0].text.lower())
        self.assertFalse(any(p.error for p in pages))

    def test_ochoa_chapter_extracts_text(self):
        path = config.RAW_OCHOA_DIR / "32-Trabajo-Energía 096-100.pdf"
        if not path.exists():
            self.skipTest("No esta extraido el capitulo de Ochoa")
        pages = extract_pdf(path)
        self.assertEqual(len(pages), 5)
        self.assertGreater(sum(p.char_count for p in pages), 10000)
        self.assertIn("trabajo", " ".join(p.text for p in pages).lower())


class ChunkingTests(unittest.TestCase):
    def test_chunk_page_short(self):
        chunks = _chunk_page("uno dos tres", "doc", 1, chunk_words=10, overlap_words=2)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].chunk_id, "doc:p1:c0")
        self.assertEqual(chunks[0].word_count, 3)

    def test_chunk_page_overlap(self):
        words = " ".join(f"w{i}" for i in range(25))
        chunks = _chunk_page(words, "doc", 2, chunk_words=10, overlap_words=3)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertEqual(chunks[1].chunk_index, 1)
        self.assertEqual(chunks[1].text.split()[0], "w7")
        self.assertEqual(chunks[2].text.split()[0], "w14")
        self.assertEqual(chunks[2].word_count, 11)

    def test_quality_empty_page(self):
        needs_ocr, flags = _page_quality("", 0)
        self.assertTrue(needs_ocr)
        self.assertIn("sin_texto", flags)

    def test_quality_good_page(self):
        text = (
            "La energia mecanica se conserva en un campo conservativo cuando "
            "las fuerzas que actuan sobre el sistema son conservativas."
        )
        needs_ocr, flags = _page_quality(text, len(text))
        self.assertFalse(needs_ocr)
        self.assertEqual(flags, [])


if __name__ == "__main__":
    unittest.main()
