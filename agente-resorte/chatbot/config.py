"""Rutas y parametros de la etapa de procesamiento de bibliografia."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BIBLIOGRAFIA_DIR = PROJECT_ROOT / "Bibliografía"
DATA_DIR = PROJECT_ROOT / "data"
CORPUS_DIR = DATA_DIR / "corpus"
RAW_OCHOA_DIR = CORPUS_DIR / "raw" / "ochoa"
INDEX_DIR = DATA_DIR / "index" / "bibliografia"
DB_PATH = INDEX_DIR / "bibliografia.sqlite"
EMBEDDINGS_DB_PATH = INDEX_DIR / "embeddings.sqlite"
PAGES_PATH = INDEX_DIR / "pages.jsonl"
CHUNKS_PATH = INDEX_DIR / "chunks.jsonl"
MANIFEST_PATH = INDEX_DIR / "manifest.json"

OCHOA_ARCHIVE = BIBLIOGRAFIA_DIR / "Ochoa.rar"
SOURCE_TYPE = "bibliografia"
INDEX_VERSION = 1
EXTRACTOR_VERSION = "pdf_text-0.1"
EMBEDDINGS_VERSION = "embeddings-0.1"

CHUNK_WORDS = 500
CHUNK_OVERLAP_WORDS = 80
MIN_PAGE_CHARS = 80
MAX_REPLACEMENT_RATIO = 0.02
MAX_CONTROL_RATIO = 0.02
MIN_ALPHA_RATIO = 0.45

# Etapa 3A: embeddings locales (BGE-M3). No se descarga nada automaticamente.
EMBEDDING_BACKEND = "ollama"  # "ollama" o "sentence_transformers"
EMBEDDING_MODEL = "bge-m3"
EMBEDDING_BATCH_SIZE = 16
OLLAMA_URL = "http://127.0.0.1:11434"
HYBRID_RRF_K = 60
