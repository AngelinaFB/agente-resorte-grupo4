import hashlib
import math
import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from chatbot.embeddings import (
    build_embeddings,
    embeddings_stats,
    hybrid_search,
    semantic_search,
)
from chatbot.index import build_index, search as fts_search


CONCEPTS = {
    "periodo": ["periodo", "oscilacion", "oscilatorio", "tiempo", "ciclo", "resorte"],
    "masa": ["masa", "inercia", "movimiento", "oscilatorio", "aceleracion"],
    "energia": ["energia", "cinetica", "potencial", "conserva", "mecanica"],
    "frecuencia": ["frecuencia", "angular", "omega", "rad", "velocidad"],
    "amortiguamiento": ["amortiguamiento", "amortiguado", "disipa", "friccion", "decae"],
}
DIM = 48


def _normalize(vec):
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def fake_embed(texts):
    vectors = []
    for text in texts:
        vec = [0.0] * DIM
        tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
        joined = " ".join(tokens)
        for i, (name, keys) in enumerate(CONCEPTS.items()):
            for key in keys:
                if key in joined:
                    vec[i] += 1.0
                    # refuerza terminos cercanos del mismo concepto
                    for j, other in enumerate(keys):
                        if other in joined and other != key:
                            vec[i] += 0.15
        # componente lexico estable para no colapsar vectores no conceptuales
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for b in digest[:12]:
                vec[12 + (b % (DIM - 12))] += 0.05
        vectors.append(_normalize(vec))
    return vectors


def sample_corpus():
    documents = [
        {
            "doc_id": "doc-fis",
            "source_path": "Bibliografía/fisica-oscilaciones.pdf",
            "source_type": "bibliografia",
            "origin": "pdf",
            "title": "fisica-oscilaciones",
            "sha256": "abc",
            "pdf_pages": 5,
            "text_pages": 5,
            "char_count": 600,
            "needs_ocr_pages": 0,
            "flagged_pages": 0,
            "chunk_count": 5,
        }
    ]
    texts = [
        (
            1,
            "El periodo de oscilacion de un resorte depende de la masa y de la constante elastica.",
        ),
        (
            2,
            "La masa influye en el movimiento oscilatorio: mayor masa produce oscilaciones mas lentas.",
        ),
        (
            3,
            "La energia cinetica y la energia potencial se transforman durante el movimiento, conservando la energia mecanica.",
        ),
        (
            4,
            "La frecuencia angular omega se obtiene a partir de la constante del sistema y permite calcular el movimiento periodico.",
        ),
        (
            5,
            "El amortiguamiento representa la disipacion de energia por friccion y hace que la amplitud decaiga con el tiempo.",
        ),
    ]
    pages = []
    chunks = []
    for page, text in texts:
        pages.append(
            {
                "doc_id": "doc-fis",
                "page": page,
                "text": text,
                "char_count": len(text),
                "word_count": len(text.split()),
                "needs_ocr": False,
                "quality_flags": [],
            }
        )
        chunks.append(
            {
                "chunk_id": f"doc-fis:p{page}:c0",
                "doc_id": "doc-fis",
                "page": page,
                "chunk_index": 0,
                "text": text,
                "word_count": len(text.split()),
                "char_count": len(text),
            }
        )
    return documents, pages, chunks


class EmbeddingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.db = root / "bibliografia.sqlite"
        self.emb = root / "embeddings.sqlite"
        docs, pages, chunks = sample_corpus()
        build_index(self.db, docs, pages, chunks)
        build_embeddings(
            db_path=self.db,
            embeddings_db_path=self.emb,
            embedder=fake_embed,
            model="test-fake-bge-m3",
            backend="fake",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_fts_index_not_modified_destructively(self):
        # El indice FTS5 sigue integro y con las mismas tablas/filas.
        conn = sqlite3.connect(str(self.db))
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type IN ('table','shadow')"
                ).fetchall()
            }
            self.assertIn("chunks_fts", tables)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0], 5)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0], 5)
        finally:
            conn.close()
        fts = fts_search("periodo", db_path=self.db)
        self.assertTrue(fts)

    def test_embeddings_db_separate_and_rebuildable(self):
        self.assertTrue(self.emb.exists())
        self.assertNotEqual(self.db.resolve(), self.emb.resolve())
        stats = embeddings_stats(self.emb)
        self.assertEqual(stats["chunks"], 5)
        self.assertEqual(stats["metadata"]["model"], "test-fake-bge-m3")
        # reconstruccion completa
        build_embeddings(
            db_path=self.db,
            embeddings_db_path=self.emb,
            embedder=fake_embed,
            model="test-fake-bge-m3",
            backend="fake",
        )
        stats2 = embeddings_stats(self.emb)
        self.assertEqual(stats2["chunks"], 5)

    def test_semantic_search_required_fields(self):
        results = semantic_search(
            "¿Qué determina el período de oscilación de un resorte?",
            db_path=self.db,
            embeddings_db_path=self.emb,
            embedder=fake_embed,
            limit=3,
        )
        self.assertTrue(results)
        first = results[0]
        for key in ("text", "source_path", "page", "chunk_id", "score", "doc_id", "title"):
            self.assertIn(key, first)
        self.assertIsInstance(first["page"], int)
        self.assertIsInstance(first["score"], float)
        self.assertEqual(first["source_path"], "Bibliografía/fisica-oscilaciones.pdf")

    def test_semantic_search_no_duplicate_chunks(self):
        results = semantic_search(
            "energia movimiento oscilatorio",
            db_path=self.db,
            embeddings_db_path=self.emb,
            embedder=fake_embed,
            limit=10,
        )
        ids = [r["chunk_id"] for r in results]
        self.assertEqual(len(ids), len(set(ids)))

    def test_hybrid_search_combines_modes(self):
        results = hybrid_search(
            "periodo de oscilacion",
            db_path=self.db,
            embeddings_db_path=self.emb,
            embedder=fake_embed,
            limit=3,
        )
        self.assertTrue(results)
        self.assertEqual(results[0]["mode"], "hybrid")
        self.assertTrue(results[0].get("sources"))

    def test_hybrid_falls_back_to_relaxed_fts_when_strict_has_no_hits(self):
        query = "¿Qué relación existe entre la energía cinética y potencial?"
        self.assertEqual(fts_search(query, db_path=self.db, limit=5), [])

        results = hybrid_search(
            query,
            db_path=self.db,
            embeddings_db_path=self.emb,
            embedder=fake_embed,
            limit=3,
        )

        self.assertTrue(
            any("fts" in item["sources"] and item["page"] == 3 for item in results),
            "La búsqueda híbrida debe recuperar por FTS si el AND estricto no encuentra resultados",
        )

    def test_conceptual_queries_retrieve_relevant_pages(self):
        cases = [
            ("¿Qué determina el período de oscilación de un resorte?", 1),
            ("¿Cómo influye la masa en el movimiento oscilatorio?", 2),
            ("¿Qué relación existe entre la energía cinética y potencial?", 3),
            ("¿Cómo se obtiene la frecuencia angular?", 4),
            ("¿Qué representa el amortiguamiento?", 5),
        ]
        for query, expected_page in cases:
            with self.subTest(query=query):
                results = semantic_search(
                    query,
                    db_path=self.db,
                    embeddings_db_path=self.emb,
                    embedder=fake_embed,
                    limit=3,
                )
                pages = [r["page"] for r in results]
                self.assertIn(
                    expected_page,
                    pages,
                    f"Consulta no recupero pagina esperada {expected_page}: {pages}",
                )
                top = results[0]
                self.assertEqual(top["doc_id"], "doc-fis")
                self.assertTrue(top["chunk_id"].startswith("doc-fis:"))

    def test_filters_by_doc_and_page(self):
        results = semantic_search(
            "energia",
            db_path=self.db,
            embeddings_db_path=self.emb,
            embedder=fake_embed,
            doc_id="doc-fis",
            page=3,
            limit=5,
        )
        self.assertTrue(results)
        self.assertTrue(all(r["page"] == 3 for r in results))
        self.assertTrue(all(r["doc_id"] == "doc-fis" for r in results))


if __name__ == "__main__":
    unittest.main()
