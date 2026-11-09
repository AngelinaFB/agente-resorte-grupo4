"""Embeddings locales (BGE-M3) y busqueda semantica/hibrida.

Etapa 3A: no usa APIs externas ni servicios en la nube. Los vectores se
almacenan en una base SQLite separada del indice FTS5 para no modificarlo de
forma destructiva. El indice de embeddings es reconstruible desde los chunks
existentes en ``config.DB_PATH``.
"""

from __future__ import annotations

import json
import sqlite3
import time
import urllib.error
import urllib.request
from array import array
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from . import config

EMBEDDINGS_SCHEMA = """
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE chunk_embeddings (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    page INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    source_path TEXT NOT NULL,
    title TEXT NOT NULL,
    model TEXT NOT NULL,
    dim INTEGER NOT NULL,
    vector BLOB NOT NULL
);

CREATE INDEX idx_chunk_embeddings_doc_page ON chunk_embeddings(doc_id, page);
"""

EmbedTexts = Callable[[Sequence[str]], list[list[float]]]


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _vector_to_blob(vector: Sequence[float]) -> bytes:
    arr = array("f", (float(x) for x in vector))
    return arr.tobytes()


def _blob_to_vector(blob: bytes) -> list[float]:
    arr = array("f")
    arr.frombytes(blob)
    return arr.tolist()


def _cosine_scores(query: Sequence[float], matrix_rows: Sequence[tuple[str, bytes]]):
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - entorno sin numpy
        raise RuntimeError("Se requiere numpy para busqueda semantica") from exc

    if not matrix_rows:
        return []
    q = np.asarray(query, dtype=np.float32)
    q_norm = float(np.linalg.norm(q))
    if q_norm == 0:
        return [(chunk_id, 0.0) for chunk_id, _ in matrix_rows]
    q = q / q_norm
    ids = []
    vecs = []
    for chunk_id, blob in matrix_rows:
        ids.append(chunk_id)
        vecs.append(np.frombuffer(blob, dtype=np.float32))
    mat = np.vstack(vecs)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = mat / norms
    scores = mat @ q
    return list(zip(ids, scores.astype(float).tolist()))


def _ollama_embed(
    texts: Sequence[str],
    model: str = config.EMBEDDING_MODEL,
    base_url: str = config.OLLAMA_URL,
    timeout: float = 120.0,
) -> list[list[float]]:
    """Genera embeddings via Ollama local. Requiere Ollama en ejecucion."""
    if not texts:
        return []
    url = base_url.rstrip("/") + "/api/embed"
    payload = json.dumps({"model": model, "input": list(texts)}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        if exc.code == 404:
            # Compatibilidad con endpoint antiguo.
            return [_ollama_embed_one(text, model, base_url, timeout) for text in texts]
        raise RuntimeError(f"Ollama devolvio HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"No se pudo conectar a Ollama en {base_url}. "
            "Verifique que Ollama este instalado y en ejecucion, y que el "
            f"modelo '{model}' este disponible localmente."
        ) from exc

    embeddings = data.get("embeddings")
    if embeddings is None and "embedding" in data:
        embeddings = [data["embedding"]]
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise RuntimeError("Respuesta de Ollama invalida para embeddings")
    return embeddings


def _ollama_embed_one(
    text: str,
    model: str,
    base_url: str,
    timeout: float,
) -> list[float]:
    url = base_url.rstrip("/") + "/api/embeddings"
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    embedding = data.get("embedding")
    if not isinstance(embedding, list):
        raise RuntimeError("Respuesta de Ollama invalida para /api/embeddings")
    return embedding


def _sentence_transformers_embed(
    texts: Sequence[str],
    model: str = "BAAI/bge-m3",
    batch_size: int = config.EMBEDDING_BATCH_SIZE,
) -> list[list[float]]:
    """Genera embeddings con sentence-transformers si el modelo esta local."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "sentence-transformers no esta instalado. Instale dependencias de "
            "requirements-chatbot.txt o use el backend Ollama."
        ) from exc

    # local_files_only evita descargas automaticas sin autorizacion.
    try:
        st_model = SentenceTransformer(model, local_files_only=True)
    except Exception as exc:
        raise RuntimeError(
            f"No se pudo cargar '{model}' localmente con sentence-transformers. "
            "El modelo debe estar disponible en cache local; no se descarga "
            "automaticamente."
        ) from exc
    vectors = st_model.encode(
        list(texts),
        batch_size=max(1, int(batch_size)),
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    return [v.astype(float).tolist() for v in vectors]


def get_embedder(
    backend: str = config.EMBEDDING_BACKEND,
    model: str = config.EMBEDDING_MODEL,
    base_url: str = config.OLLAMA_URL,
    batch_size: int = config.EMBEDDING_BATCH_SIZE,
) -> EmbedTexts:
    backend = (backend or "").strip().lower()
    if backend == "ollama":
        return lambda texts: _ollama_embed(texts, model=model, base_url=base_url)
    if backend in {"sentence_transformers", "sentence-transformers", "st"}:
        st_model = model
        if model == "bge-m3":
            st_model = "BAAI/bge-m3"
        return lambda texts: _sentence_transformers_embed(
            texts, model=st_model, batch_size=batch_size
        )
    raise ValueError(f"Backend de embeddings no soportado: {backend}")


def _fetch_chunks(db_path: Path) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT c.chunk_id, c.doc_id, c.page, c.chunk_index, c.text,
                   c.word_count, c.char_count, d.source_path, d.title
            FROM chunks c
            JOIN documents d ON d.doc_id = c.doc_id
            ORDER BY c.doc_id, c.page, c.chunk_index
            """
        ).fetchall()
    finally:
        conn.close()
    return [dict(row) for row in rows]


def build_embeddings(
    db_path: Path = config.DB_PATH,
    embeddings_db_path: Path = config.EMBEDDINGS_DB_PATH,
    embedder: EmbedTexts | None = None,
    backend: str = config.EMBEDDING_BACKEND,
    model: str = config.EMBEDDING_MODEL,
    batch_size: int = config.EMBEDDING_BATCH_SIZE,
    base_url: str = config.OLLAMA_URL,
    limit: int | None = None,
    progress: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Construye o reconstruye el indice de embeddings desde chunks FTS5.

    No modifica ``db_path``. Reemplaza completamente ``embeddings_db_path``.
    """
    if not Path(db_path).exists():
        raise FileNotFoundError(f"No existe el indice de chunks {db_path}")
    chunks = _fetch_chunks(Path(db_path))
    if limit is not None:
        chunks = chunks[: max(0, int(limit))]
    if not chunks:
        raise RuntimeError("No hay chunks para indexar")

    if embedder is None:
        embedder = get_embedder(
            backend=backend,
            model=model,
            base_url=base_url,
            batch_size=batch_size,
        )

    embeddings_db_path = Path(embeddings_db_path)
    embeddings_db_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(embeddings_db_path) + suffix)
        if candidate.exists():
            candidate.unlink()

    started = time.perf_counter()
    dim = None
    total = len(chunks)
    conn = _connect(embeddings_db_path)
    try:
        conn.executescript(EMBEDDINGS_SCHEMA)
        for start in range(0, total, max(1, int(batch_size))):
            batch = chunks[start : start + batch_size]
            vectors = embedder([item["text"] for item in batch])
            if len(vectors) != len(batch):
                raise RuntimeError(
                    "El backend de embeddings devolvio una cantidad incorrecta "
                    f"de vectores ({len(vectors)} != {len(batch)})"
                )
            rows = []
            for item, vector in zip(batch, vectors):
                if dim is None:
                    dim = len(vector)
                elif len(vector) != dim:
                    raise RuntimeError(
                        f"Dimension inconsistente: esperado {dim}, obtenido {len(vector)}"
                    )
                rows.append(
                    (
                        item["chunk_id"],
                        item["doc_id"],
                        item["page"],
                        item["chunk_index"],
                        item["source_path"],
                        item["title"],
                        model,
                        dim,
                        _vector_to_blob(vector),
                    )
                )
            conn.executemany(
                """
                INSERT INTO chunk_embeddings (
                    chunk_id, doc_id, page, chunk_index, source_path, title,
                    model, dim, vector
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
            if progress:
                progress(min(start + len(batch), total), total)

        elapsed = time.perf_counter() - started
        metadata = {
            "embeddings_version": config.EMBEDDINGS_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_db": str(db_path),
            "backend": backend,
            "model": model,
            "chunks": str(total),
            "dim": str(dim or 0),
            "batch_size": str(batch_size),
            "seconds": f"{elapsed:.6f}",
        }
        conn.executemany(
            "INSERT INTO metadata (key, value) VALUES (?, ?)",
            list(metadata.items()),
        )
        conn.commit()
    finally:
        conn.close()

    return {
        "ok": True,
        "embeddings_db": str(embeddings_db_path),
        "chunks": total,
        "dim": dim,
        "model": model,
        "backend": backend,
        "seconds": round(elapsed, 3),
    }


def embeddings_stats(
    embeddings_db_path: Path = config.EMBEDDINGS_DB_PATH,
) -> dict[str, Any]:
    if not Path(embeddings_db_path).exists():
        raise FileNotFoundError(
            f"No existe el indice de embeddings {embeddings_db_path}"
        )
    conn = _connect(embeddings_db_path)
    try:
        meta_rows = conn.execute("SELECT key, value FROM metadata").fetchall()
        counts = conn.execute(
            "SELECT COUNT(*) AS chunks, MIN(dim) AS min_dim, MAX(dim) AS max_dim "
            "FROM chunk_embeddings"
        ).fetchone()
    finally:
        conn.close()
    return {
        "metadata": {row["key"]: row["value"] for row in meta_rows},
        "chunks": counts["chunks"],
        "min_dim": counts["min_dim"],
        "max_dim": counts["max_dim"],
    }


def _join_page_quality(
    conn: sqlite3.Connection,
    db_path: Path,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Adjunta marcas de calidad de pagina cuando la BD principal es accesible."""
    if not rows or not Path(db_path).exists():
        for row in rows:
            row.setdefault("needs_ocr", None)
            row.setdefault("quality_flags", None)
        return rows
    attached = "mainidx"
    conn.execute(f"ATTACH DATABASE ? AS {attached}", (str(db_path),))
    try:
        for row in rows:
            page = conn.execute(
                f"SELECT needs_ocr, quality_flags FROM {attached}.pages "
                "WHERE doc_id = ? AND page = ?",
                (row["doc_id"], row["page"]),
            ).fetchone()
            if page:
                row["needs_ocr"] = bool(page["needs_ocr"])
                try:
                    row["quality_flags"] = json.loads(page["quality_flags"])
                except Exception:
                    row["quality_flags"] = []
            else:
                row["needs_ocr"] = None
                row["quality_flags"] = None
    finally:
        conn.execute(f"DETACH DATABASE {attached}")
    return rows


def semantic_search(
    query: str,
    db_path: Path = config.DB_PATH,
    embeddings_db_path: Path = config.EMBEDDINGS_DB_PATH,
    limit: int = 5,
    doc_id: str | None = None,
    page: int | None = None,
    embedder: EmbedTexts | None = None,
    backend: str = config.EMBEDDING_BACKEND,
    model: str = config.EMBEDDING_MODEL,
    base_url: str = config.OLLAMA_URL,
) -> list[dict[str, Any]]:
    """Busca chunks por similitud semantica."""
    query = (query or "").strip()
    if not query:
        return []
    if not Path(embeddings_db_path).exists():
        raise FileNotFoundError(
            f"No existe el indice de embeddings {embeddings_db_path}"
        )
    limit = max(1, min(int(limit), 50))
    if embedder is None:
        embedder = get_embedder(backend=backend, model=model, base_url=base_url)
    query_vector = embedder([query])[0]

    conn = _connect(embeddings_db_path)
    try:
        where = []
        params: list[Any] = []
        if doc_id:
            where.append("doc_id = ?")
            params.append(doc_id)
        if page is not None:
            where.append("page = ?")
            params.append(int(page))
        sql = (
            "SELECT chunk_id, doc_id, page, chunk_index, source_path, title, vector "
            "FROM chunk_embeddings"
        )
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = conn.execute(sql, params).fetchall()
        scored = _cosine_scores(query_vector, [(r["chunk_id"], r["vector"]) for r in rows])
        scored.sort(key=lambda item: item[1], reverse=True)
        top = scored[:limit]
        row_map = {r["chunk_id"]: r for r in rows}
        results = []
        for chunk_id, score in top:
            row = row_map[chunk_id]
            results.append(
                {
                    "chunk_id": chunk_id,
                    "doc_id": row["doc_id"],
                    "source_path": row["source_path"],
                    "title": row["title"],
                    "page": row["page"],
                    "chunk_index": row["chunk_index"],
                    "score": float(score),
                    "mode": "semantic",
                }
            )
        # Obtener texto del chunk desde BD principal si existe.
        if Path(db_path).exists():
            attached = "mainidx"
            conn.execute(f"ATTACH DATABASE ? AS {attached}", (str(db_path),))
            try:
                for row in results:
                    chunk = conn.execute(
                        f"SELECT text FROM {attached}.chunks WHERE chunk_id = ?",
                        (row["chunk_id"],),
                    ).fetchone()
                    row["text"] = chunk["text"] if chunk else ""
            finally:
                conn.execute(f"DETACH DATABASE {attached}")
        else:
            for row in results:
                row["text"] = ""
        _join_page_quality(conn, db_path, results)
    finally:
        conn.close()
    return results


def _rrf_merge(
    rankings: Sequence[Sequence[dict[str, Any]]],
    limit: int,
    k: int = config.HYBRID_RRF_K,
) -> list[dict[str, Any]]:
    scores: dict[str, float] = {}
    items: dict[str, dict[str, Any]] = {}
    modes: dict[str, set[str]] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            cid = item["chunk_id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
            modes.setdefault(cid, set()).add(item.get("mode", "unknown"))
            if cid not in items:
                items[cid] = dict(item)
    merged = []
    for cid, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]:
        item = dict(items[cid])
        item["score"] = float(score)
        item["mode"] = "hybrid"
        item["sources"] = sorted(modes[cid])
        merged.append(item)
    return merged


def hybrid_search(
    query: str,
    db_path: Path = config.DB_PATH,
    embeddings_db_path: Path = config.EMBEDDINGS_DB_PATH,
    limit: int = 5,
    doc_id: str | None = None,
    page: int | None = None,
    embedder: EmbedTexts | None = None,
    backend: str = config.EMBEDDING_BACKEND,
    model: str = config.EMBEDDING_MODEL,
    base_url: str = config.OLLAMA_URL,
    rrf_k: int = config.HYBRID_RRF_K,
) -> list[dict[str, Any]]:
    """Combina FTS5 y semantica con Reciprocal Rank Fusion."""
    query = (query or "").strip()
    if not query:
        return []
    limit = max(1, min(int(limit), 50))
    candidate_limit = min(50, max(limit * 4, limit))
    from .index import search as fts_search

    fts_results = fts_search(
        query, db_path=db_path, limit=candidate_limit, doc_id=doc_id, page=page
    )
    # Las consultas en lenguaje natural suelen incluir palabras funcionales o
    # verbos que no aparecen literalmente en los PDF. Si el AND estricto no
    # encuentra nada, recuperar por términos de contenido con OR evita dejar
    # que la búsqueda híbrida se convierta silenciosamente en solo semántica.
    if not fts_results:
        fts_results = fts_search(
            query,
            db_path=db_path,
            limit=candidate_limit,
            doc_id=doc_id,
            page=page,
            match_any=True,
        )
    for item in fts_results:
        item["mode"] = "fts"
    semantic_results = semantic_search(
        query,
        db_path=db_path,
        embeddings_db_path=embeddings_db_path,
        limit=candidate_limit,
        doc_id=doc_id,
        page=page,
        embedder=embedder,
        backend=backend,
        model=model,
        base_url=base_url,
    )
    return _rrf_merge([fts_results, semantic_results], limit=limit, k=rrf_k)
