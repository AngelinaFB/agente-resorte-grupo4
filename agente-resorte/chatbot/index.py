"""Indice local SQLite FTS5 para la bibliografia procesada."""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import config

SCHEMA = """
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    source_path TEXT NOT NULL,
    source_type TEXT NOT NULL,
    origin TEXT NOT NULL,
    title TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    pdf_pages INTEGER NOT NULL,
    text_pages INTEGER NOT NULL,
    char_count INTEGER NOT NULL,
    needs_ocr_pages INTEGER NOT NULL,
    flagged_pages INTEGER NOT NULL,
    chunk_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE pages (
    doc_id TEXT NOT NULL,
    page INTEGER NOT NULL,
    char_count INTEGER NOT NULL,
    word_count INTEGER NOT NULL,
    needs_ocr INTEGER NOT NULL,
    quality_flags TEXT NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (doc_id, page),
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id TEXT UNIQUE NOT NULL,
    doc_id TEXT NOT NULL,
    page INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    char_count INTEGER NOT NULL,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

CREATE INDEX idx_chunks_doc_page ON chunks(doc_id, page);

CREATE VIRTUAL TABLE chunks_fts USING fts5(
    chunk_id UNINDEXED,
    text,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def build_index(
    db_path: Path,
    documents: list[dict[str, Any]],
    pages: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
) -> None:
    """Reconstruye el indice desde cero."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_path) + suffix)
        if candidate.exists():
            candidate.unlink()

    conn = _connect(db_path)
    try:
        conn.executescript(SCHEMA)
        now = datetime.now(timezone.utc).isoformat()
        conn.executemany(
            """
            INSERT INTO documents (
                doc_id, source_path, source_type, origin, title, sha256,
                pdf_pages, text_pages, char_count, needs_ocr_pages,
                flagged_pages, chunk_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    d["doc_id"],
                    d["source_path"],
                    d["source_type"],
                    d["origin"],
                    d["title"],
                    d["sha256"],
                    d["pdf_pages"],
                    d["text_pages"],
                    d["char_count"],
                    d["needs_ocr_pages"],
                    d["flagged_pages"],
                    d["chunk_count"],
                    now,
                )
                for d in documents
            ],
        )
        conn.executemany(
            """
            INSERT INTO pages (
                doc_id, page, char_count, word_count, needs_ocr,
                quality_flags, text
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    p["doc_id"],
                    p["page"],
                    p["char_count"],
                    p["word_count"],
                    int(bool(p["needs_ocr"])),
                    json.dumps(p["quality_flags"], ensure_ascii=False),
                    p["text"],
                )
                for p in pages
            ],
        )
        conn.executemany(
            """
            INSERT INTO chunks (
                chunk_id, doc_id, page, chunk_index, text, word_count, char_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    c["chunk_id"],
                    c["doc_id"],
                    c["page"],
                    c["chunk_index"],
                    c["text"],
                    c["word_count"],
                    c["char_count"],
                )
                for c in chunks
            ],
        )
        conn.executemany(
            "INSERT INTO chunks_fts (chunk_id, text) VALUES (?, ?)",
            [(c["chunk_id"], c["text"]) for c in chunks],
        )
        conn.commit()
        conn.execute("PRAGMA optimize")
    finally:
        conn.close()


def _fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    return " ".join(f'"{token}"' for token in tokens)


def search(
    query: str,
    db_path: Path = config.DB_PATH,
    limit: int = 5,
    doc_id: str | None = None,
    page: int | None = None,
) -> list[dict[str, Any]]:
    fts = _fts_query(query)
    if not fts:
        return []
    limit = max(1, min(int(limit), 50))
    where = ["chunks_fts MATCH ?"]
    params: list[Any] = [fts]
    if doc_id:
        where.append("c.doc_id = ?")
        params.append(doc_id)
    if page is not None:
        where.append("c.page = ?")
        params.append(int(page))
    params.append(limit)
    sql = f"""
        SELECT
            c.chunk_id,
            c.doc_id,
            d.source_path,
            d.title,
            c.page,
            c.chunk_index,
            c.text,
            snippet(chunks_fts, 1, '«', '»', '…', 24) AS snippet,
            bm25(chunks_fts) AS rank
        FROM chunks_fts
        JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
        JOIN documents d ON d.doc_id = c.doc_id
        WHERE {' AND '.join(where)}
        ORDER BY rank
        LIMIT ?
    """
    conn = _connect(db_path)
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    return [
        {
            "chunk_id": row["chunk_id"],
            "doc_id": row["doc_id"],
            "source_path": row["source_path"],
            "title": row["title"],
            "page": row["page"],
            "chunk_index": row["chunk_index"],
            "text": row["text"],
            "snippet": row["snippet"],
            "score": -float(row["rank"]),
        }
        for row in rows
    ]


def stats(db_path: Path = config.DB_PATH) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"No existe el indice {db_path}")
    conn = _connect(db_path)
    try:
        totals = conn.execute(
            """
            SELECT
                COUNT(*) AS documents,
                COALESCE(SUM(pdf_pages), 0) AS pdf_pages,
                COALESCE(SUM(text_pages), 0) AS text_pages,
                COALESCE(SUM(char_count), 0) AS char_count,
                COALESCE(SUM(chunk_count), 0) AS chunks,
                COALESCE(SUM(needs_ocr_pages), 0) AS needs_ocr_pages,
                COALESCE(SUM(flagged_pages), 0) AS flagged_pages
            FROM documents
            """
        ).fetchone()
        documents = [
            dict(row)
            for row in conn.execute(
                """
                SELECT
                    doc_id, source_path, origin, title, pdf_pages, text_pages,
                    char_count, needs_ocr_pages, flagged_pages, chunk_count
                FROM documents
                ORDER BY source_path
                """
            ).fetchall()
        ]
        fts_count = conn.execute("SELECT COUNT(*) FROM chunks_fts").fetchone()[0]
    finally:
        conn.close()
    result = dict(totals)
    result["fts_rows"] = fts_count
    result["documents_detail"] = documents
    return result


def verify_index(db_path: Path = config.DB_PATH) -> dict[str, Any]:
    if not db_path.exists():
        raise FileNotFoundError(f"No existe el indice {db_path}")
    checks: dict[str, Any] = {}
    errors: list[str] = []
    conn = _connect(db_path)
    try:
        checks["integrity_check"] = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if checks["integrity_check"] != "ok":
            errors.append("PRAGMA integrity_check no devolvio ok")

        counts = {}
        for table in ("documents", "pages", "chunks", "chunks_fts"):
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        checks["counts"] = counts
        if counts["chunks"] != counts["chunks_fts"]:
            errors.append("chunks y chunks_fts tienen distinto numero de filas")

        orphan_pages = conn.execute(
            """
            SELECT COUNT(*) FROM pages p
            LEFT JOIN documents d ON d.doc_id = p.doc_id
            WHERE d.doc_id IS NULL
            """
        ).fetchone()[0]
        orphan_chunks = conn.execute(
            """
            SELECT COUNT(*) FROM chunks c
            LEFT JOIN documents d ON d.doc_id = c.doc_id
            LEFT JOIN pages p ON p.doc_id = c.doc_id AND p.page = c.page
            WHERE d.doc_id IS NULL OR p.doc_id IS NULL
            """
        ).fetchone()[0]
        checks["orphan_pages"] = orphan_pages
        checks["orphan_chunks"] = orphan_chunks
        if orphan_pages:
            errors.append(f"{orphan_pages} paginas sin documento")
        if orphan_chunks:
            errors.append(f"{orphan_chunks} chunks sin documento o pagina")

        duplicate_chunks = conn.execute(
            "SELECT COUNT(*) FROM (SELECT chunk_id FROM chunks GROUP BY chunk_id HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        checks["duplicate_chunks"] = duplicate_chunks
        if duplicate_chunks:
            errors.append(f"{duplicate_chunks} chunk_id duplicados")

        checks["empty_chunks"] = conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE TRIM(text) = ''"
        ).fetchone()[0]
        if checks["empty_chunks"]:
            errors.append(f"{checks['empty_chunks']} chunks vacios")
    finally:
        conn.close()
    return {"ok": not errors, "checks": checks, "errors": errors}
