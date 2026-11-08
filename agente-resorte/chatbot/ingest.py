"""Extraccion, chunking y construccion del indice de la bibliografia."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from . import config
from .pdf_text import extract_pdf_bytes


@dataclass(frozen=True)
class Source:
    path: Path
    source_path: str
    origin: str


@dataclass
class PageRecord:
    doc_id: str
    page: int
    text: str
    char_count: int
    word_count: int
    needs_ocr: bool
    quality_flags: list[str] = field(default_factory=list)


@dataclass
class ChunkRecord:
    chunk_id: str
    doc_id: str
    page: int
    chunk_index: int
    text: str
    word_count: int
    char_count: int


@dataclass
class DocumentRecord:
    doc_id: str
    source_path: str
    source_type: str
    origin: str
    title: str
    sha256: str
    pdf_pages: int
    text_pages: int
    char_count: int
    needs_ocr_pages: int
    flagged_pages: int
    chunk_count: int
    pages: list[PageRecord]
    chunks: list[ChunkRecord]
    warnings: list[str] = field(default_factory=list)


def _relative(path: Path) -> str:
    return path.relative_to(config.PROJECT_ROOT).as_posix()


def _doc_id(data: bytes) -> str:
    return "bib-" + hashlib.sha256(data).hexdigest()[:16]


def ensure_ochoa_extracted(force: bool = False) -> Path:
    """Extrae Ochoa.rar con tar.exe (soporta RAR5 en este equipo)."""
    if not config.OCHOA_ARCHIVE.exists():
        raise FileNotFoundError(f"No existe {config.OCHOA_ARCHIVE}")
    config.RAW_OCHOA_DIR.mkdir(parents=True, exist_ok=True)
    existing = sorted(config.RAW_OCHOA_DIR.glob("*.pdf"))
    if existing and not force:
        return config.RAW_OCHOA_DIR
    if force:
        for pdf in existing:
            pdf.unlink()
    tar = shutil.which("tar")
    if tar is None:
        raise RuntimeError("No se encontro tar.exe para extraer Ochoa.rar")
    archive = _relative(config.OCHOA_ARCHIVE)
    dest = _relative(config.RAW_OCHOA_DIR)
    subprocess.run(
        [tar, "-xf", archive, "-C", dest],
        cwd=config.PROJECT_ROOT,
        check=True,
        capture_output=True,
    )
    if not list(config.RAW_OCHOA_DIR.glob("*.pdf")):
        raise RuntimeError("La extraccion de Ochoa.rar no produjo PDF")
    return config.RAW_OCHOA_DIR


def discover_sources(force_rar: bool = False) -> list[Source]:
    """Lista solo PDF dentro de Bibliografia y los capitulos de Ochoa.rar."""
    if not config.BIBLIOGRAFIA_DIR.exists():
        raise FileNotFoundError(f"No existe {config.BIBLIOGRAFIA_DIR}")
    sources: list[Source] = []
    for path in sorted(config.BIBLIOGRAFIA_DIR.glob("*.pdf")):
        sources.append(Source(path=path, source_path=_relative(path), origin="pdf"))
    if config.OCHOA_ARCHIVE.exists():
        raw_dir = ensure_ochoa_extracted(force=force_rar)
        for path in sorted(raw_dir.glob("*.pdf")):
            sources.append(
                Source(
                    path=path,
                    source_path=f"{_relative(config.OCHOA_ARCHIVE)}!/{path.name}",
                    origin="rar",
                )
            )
    return sources


def _page_quality(text: str, char_count: int) -> tuple[bool, list[str]]:
    flags: list[str] = []
    if char_count < config.MIN_PAGE_CHARS:
        flags.append("posible_ocr")
    if char_count == 0:
        flags.append("sin_texto")
        return True, flags
    if char_count < 20:
        flags.append("texto_insuficiente")
    replacement_ratio = text.count("\ufffd") / max(1, len(text))
    if replacement_ratio > config.MAX_REPLACEMENT_RATIO:
        flags.append("reemplazos_unicode")
    control_ratio = sum(
        1 for ch in text if ord(ch) < 32 and ch not in "\n\r\t"
    ) / max(1, len(text))
    if control_ratio > config.MAX_CONTROL_RATIO:
        flags.append("caracteres_control")
    visible = [ch for ch in text if not ch.isspace()]
    alpha_ratio = sum(ch.isalpha() for ch in visible) / max(1, len(visible))
    if alpha_ratio < config.MIN_ALPHA_RATIO:
        flags.append("baja_proporcion_alfabetica")
    words = re.findall(r"\S+", text)
    if words and sum(len(w) >= 2 for w in words) / len(words) < 0.5:
        flags.append("palabras_muy_cortas")
    needs_ocr = "posible_ocr" in flags
    return needs_ocr, flags


def _chunk_page(
    text: str,
    doc_id: str,
    page: int,
    chunk_words: int = config.CHUNK_WORDS,
    overlap_words: int = config.CHUNK_OVERLAP_WORDS,
) -> list[ChunkRecord]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    chunks: list[ChunkRecord] = []
    start = 0
    index = 0
    while start < len(words):
        end = min(start + chunk_words, len(words))
        if len(words) - end <= overlap_words:
            end = len(words)
        chunk_text = " ".join(words[start:end])
        chunks.append(
            ChunkRecord(
                chunk_id=f"{doc_id}:p{page}:c{index}",
                doc_id=doc_id,
                page=page,
                chunk_index=index,
                text=chunk_text,
                word_count=end - start,
                char_count=len(chunk_text),
            )
        )
        if end == len(words):
            break
        start = end - overlap_words
        index += 1
    return chunks


def _read_document(source: Source, seen_ids: set[str]) -> DocumentRecord:
    data = source.path.read_bytes()
    doc_id = _doc_id(data)
    if doc_id in seen_ids:
        suffix = 2
        while f"{doc_id}-{suffix}" in seen_ids:
            suffix += 1
        doc_id = f"{doc_id}-{suffix}"
    seen_ids.add(doc_id)

    pages = extract_pdf_bytes(data)
    page_records: list[PageRecord] = []
    chunks: list[ChunkRecord] = []
    for page in pages:
        text = page.text
        char_count = len(text)
        word_count = len(re.findall(r"\S+", text))
        needs_ocr, flags = _page_quality(text, char_count)
        page_records.append(
            PageRecord(
                doc_id=doc_id,
                page=page.number,
                text=text,
                char_count=char_count,
                word_count=word_count,
                needs_ocr=needs_ocr,
                quality_flags=flags,
            )
        )
        if not needs_ocr and char_count >= config.MIN_PAGE_CHARS:
            chunks.extend(_chunk_page(text, doc_id, page.number))

    return DocumentRecord(
        doc_id=doc_id,
        source_path=source.source_path,
        source_type=config.SOURCE_TYPE,
        origin=source.origin,
        title=source.path.stem,
        sha256=hashlib.sha256(data).hexdigest(),
        pdf_pages=len(pages),
        text_pages=sum(1 for p in page_records if p.char_count > 0),
        char_count=sum(p.char_count for p in page_records),
        needs_ocr_pages=sum(1 for p in page_records if p.needs_ocr),
        flagged_pages=sum(1 for p in page_records if p.quality_flags),
        chunk_count=len(chunks),
        pages=page_records,
        chunks=chunks,
    )


def _write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def ingest_bibliography(force_rar: bool = False) -> dict:
    """Procesa toda la bibliografia, escribe JSONL y construye SQLite FTS5."""
    from .index import build_index

    config.INDEX_DIR.mkdir(parents=True, exist_ok=True)
    sources = discover_sources(force_rar=force_rar)
    if not sources:
        raise RuntimeError("No se encontraron PDF en Bibliografia")

    seen_ids: set[str] = set()
    documents: list[DocumentRecord] = []
    warnings: list[str] = []
    for i, source in enumerate(sources, 1):
        print(f"[{i}/{len(sources)}] {source.source_path}", flush=True)
        try:
            document = _read_document(source, seen_ids)
        except Exception as exc:
            warning = f"Error procesando {source.source_path}: {exc}"
            warnings.append(warning)
            print("  ADVERTENCIA:", warning, flush=True)
            continue
        documents.append(document)
        print(
            f"  {document.pdf_pages} paginas, {document.char_count} chars, "
            f"{document.chunk_count} chunks, OCR {document.needs_ocr_pages}, "
            f"flags {document.flagged_pages}",
            flush=True,
        )

    if not documents:
        raise RuntimeError("Ningun PDF pudo procesarse")

    all_pages = [asdict(page) for doc in documents for page in doc.pages]
    all_chunks = [asdict(chunk) for doc in documents for chunk in doc.chunks]
    _write_jsonl(config.PAGES_PATH, all_pages)
    _write_jsonl(config.CHUNKS_PATH, all_chunks)

    doc_rows = [
        {
            "doc_id": doc.doc_id,
            "source_path": doc.source_path,
            "source_type": doc.source_type,
            "origin": doc.origin,
            "title": doc.title,
            "sha256": doc.sha256,
            "pdf_pages": doc.pdf_pages,
            "text_pages": doc.text_pages,
            "char_count": doc.char_count,
            "needs_ocr_pages": doc.needs_ocr_pages,
            "flagged_pages": doc.flagged_pages,
            "chunk_count": doc.chunk_count,
        }
        for doc in documents
    ]
    build_index(config.DB_PATH, doc_rows, all_pages, all_chunks)

    ocr_pages = [
        {
            "doc_id": page.doc_id,
            "source_path": next(
                doc.source_path for doc in documents if doc.doc_id == page.doc_id
            ),
            "page": page.page,
            "char_count": page.char_count,
            "quality_flags": page.quality_flags,
        }
        for page in (p for doc in documents for p in doc.pages)
        if page.needs_ocr
    ]
    flagged_pages = [
        {
            "doc_id": page.doc_id,
            "source_path": next(
                doc.source_path for doc in documents if doc.doc_id == page.doc_id
            ),
            "page": page.page,
            "char_count": page.char_count,
            "quality_flags": page.quality_flags,
        }
        for page in (p for doc in documents for p in doc.pages)
        if page.quality_flags
    ]
    manifest = {
        "index_version": config.INDEX_VERSION,
        "extractor_version": config.EXTRACTOR_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "bibliografia_dir": _relative(config.BIBLIOGRAFIA_DIR),
        "chunk_words": config.CHUNK_WORDS,
        "chunk_overlap_words": config.CHUNK_OVERLAP_WORDS,
        "min_page_chars": config.MIN_PAGE_CHARS,
        "totals": {
            "documents": len(documents),
            "pdf_pages": sum(doc.pdf_pages for doc in documents),
            "text_pages": sum(doc.text_pages for doc in documents),
            "char_count": sum(doc.char_count for doc in documents),
            "chunks": len(all_chunks),
            "needs_ocr_pages": len(ocr_pages),
            "flagged_pages": len(flagged_pages),
        },
        "documents": doc_rows,
        "ocr_pages": ocr_pages,
        "flagged_pages": flagged_pages,
        "warnings": warnings,
    }
    config.MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest
