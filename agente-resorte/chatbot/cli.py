"""CLI local para ingestar, consultar y verificar la bibliografia."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import config
from .embeddings import (
    build_embeddings,
    embeddings_stats,
    hybrid_search,
    semantic_search,
)
from .generation import DEFAULT_GENERATION_MODEL, answer_question
from .evaluation import evaluate_stage_3c
from .index import search, stats, verify_index
from .ingest import ingest_bibliography


def _print_manifest(manifest: dict) -> None:
    totals = manifest["totals"]
    print("Documentos:", totals["documents"])
    print("Paginas PDF:", totals["pdf_pages"])
    print("Paginas con texto:", totals["text_pages"])
    print("Caracteres:", totals["char_count"])
    print("Chunks:", totals["chunks"])
    print("Paginas que requieren OCR:", totals["needs_ocr_pages"])
    print("Paginas marcadas por calidad:", totals["flagged_pages"])
    print("Indice:", config.DB_PATH)
    print("Manifest:", config.MANIFEST_PATH)
    if manifest.get("warnings"):
        print("\nAdvertencias:")
        for warning in manifest["warnings"]:
            print(" -", warning)
    if manifest.get("ocr_pages"):
        print("\nPaginas que requieren OCR:")
        for item in manifest["ocr_pages"]:
            flags = ",".join(item["quality_flags"])
            print(
                f" - {item['source_path']} p.{item['page']} "
                f"({item['char_count']} chars) [{flags}]"
            )


def _print_stats(data: dict) -> None:
    print("Documentos:", data["documents"])
    print("Paginas PDF:", data["pdf_pages"])
    print("Paginas con texto:", data["text_pages"])
    print("Caracteres:", data["char_count"])
    print("Chunks:", data["chunks"])
    print("Filas FTS:", data["fts_rows"])
    print("Paginas que requieren OCR:", data["needs_ocr_pages"])
    print("Paginas marcadas por calidad:", data["flagged_pages"])
    print("\nDocumentos:")
    for doc in data["documents_detail"]:
        print(
            f" - {doc['source_path']} | {doc['pdf_pages']} p | "
            f"{doc['char_count']} chars | {doc['chunk_count']} chunks | "
            f"OCR {doc['needs_ocr_pages']} | flags {doc['flagged_pages']}"
        )


def _print_results(query: str, results: list[dict], mode: str = "") -> None:
    label = f" ({mode})" if mode else ""
    print(f"Consulta{label}: {query}")
    if not results:
        print("Sin resultados.")
        return
    for i, result in enumerate(results, 1):
        extra = ""
        if result.get("sources"):
            extra = f" sources={','.join(result['sources'])}"
        print(
            f"\n[{i}] {result['source_path']} p.{result['page']} "
            f"chunk {result.get('chunk_index', '?')} score={result['score']:.4f}{extra}"
        )
        preview = result.get("snippet") or result.get("text", "")
        preview = str(preview).replace("\n", " ")
        if len(preview) > 220:
            preview = preview[:217] + "..."
        print("   ", preview)
        if result.get("quality_flags"):
            print("    calidad:", ",".join(result["quality_flags"]))


def _print_answer(result: dict) -> None:
    print("Respuesta:")
    print(result["answer"])
    print(f"\nModelo: {result['model']} ({result['backend']})")
    print(f"Tiempo: {result['elapsed_seconds']:.2f} s")
    if not result["references"]:
        print("\nSin fragmentos de referencia.")
        return
    print("\nFragmentos recuperados y enviados como contexto:")
    for ref in result["references"]:
        print(
            f"\n[{ref['id']}] {ref['document']} p.{ref['page']} "
            f"(chunk {ref['chunk_id']})"
        )
        if ref.get("needs_ocr") or ref.get("quality_flags"):
            flags = list(ref.get("quality_flags") or [])
            if ref.get("needs_ocr"):
                flags.insert(0, "requiere OCR")
            print("    calidad:", ",".join(flags))
        print("    ", ref["text"].replace("\n", " "))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m chatbot.cli",
        description="Procesamiento e indice local de la bibliografia.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Procesar Bibliografia y reconstruir el indice")
    p_ingest.add_argument(
        "--force-rar", action="store_true", help="Volver a extraer Ochoa.rar"
    )
    p_ingest.add_argument("--json", action="store_true", help="Salida JSON")

    p_stats = sub.add_parser("stats", help="Mostrar estadisticas del indice")
    p_stats.add_argument("--json", action="store_true", help="Salida JSON")

    p_search = sub.add_parser("search", help="Buscar fragmentos en el indice")
    p_search.add_argument("query", help="Texto a buscar")
    p_search.add_argument("--limit", type=int, default=5, help="Maximo de resultados")
    p_search.add_argument("--doc-id", help="Filtrar por doc_id")
    p_search.add_argument("--page", type=int, help="Filtrar por pagina")
    p_search.add_argument("--json", action="store_true", help="Salida JSON")

    p_verify = sub.add_parser("verify", help="Verificar integridad del indice")
    p_verify.add_argument("--json", action="store_true", help="Salida JSON")

    p_embed = sub.add_parser(
        "embed-build", help="Construir indice de embeddings desde chunks existentes"
    )
    p_embed.add_argument("--backend", default=config.EMBEDDING_BACKEND)
    p_embed.add_argument("--model", default=config.EMBEDDING_MODEL)
    p_embed.add_argument("--ollama-url", default=config.OLLAMA_URL)
    p_embed.add_argument("--batch-size", type=int, default=config.EMBEDDING_BATCH_SIZE)
    p_embed.add_argument("--limit", type=int, help="Limitar chunks (pruebas)")
    p_embed.add_argument("--json", action="store_true", help="Salida JSON")

    p_embed_stats = sub.add_parser("embed-stats", help="Estadisticas de embeddings")
    p_embed_stats.add_argument("--json", action="store_true", help="Salida JSON")

    p_sem = sub.add_parser("search-semantic", help="Busqueda semantica por embeddings")
    p_sem.add_argument("query", help="Texto a buscar")
    p_sem.add_argument("--limit", type=int, default=5, help="Maximo de resultados")
    p_sem.add_argument("--doc-id", help="Filtrar por doc_id")
    p_sem.add_argument("--page", type=int, help="Filtrar por pagina")
    p_sem.add_argument("--backend", default=config.EMBEDDING_BACKEND)
    p_sem.add_argument("--model", default=config.EMBEDDING_MODEL)
    p_sem.add_argument("--ollama-url", default=config.OLLAMA_URL)
    p_sem.add_argument("--json", action="store_true", help="Salida JSON")

    p_hyb = sub.add_parser("search-hybrid", help="Busqueda hibrida FTS5 + semantica")
    p_hyb.add_argument("query", help="Texto a buscar")
    p_hyb.add_argument("--limit", type=int, default=5, help="Maximo de resultados")
    p_hyb.add_argument("--doc-id", help="Filtrar por doc_id")
    p_hyb.add_argument("--page", type=int, help="Filtrar por pagina")
    p_hyb.add_argument("--backend", default=config.EMBEDDING_BACKEND)
    p_hyb.add_argument("--model", default=config.EMBEDDING_MODEL)
    p_hyb.add_argument("--ollama-url", default=config.OLLAMA_URL)
    p_hyb.add_argument("--json", action="store_true", help="Salida JSON")

    p_ask = sub.add_parser("ask", help="Responder con bibliografia usando Ollama local")
    p_ask.add_argument("question", help="Pregunta academica")
    p_ask.add_argument("--limit", type=int, default=5, help="Fragmentos de contexto")
    p_ask.add_argument("--model", default=DEFAULT_GENERATION_MODEL)
    p_ask.add_argument("--ollama-url", default=config.OLLAMA_URL)
    p_ask.add_argument("--json", action="store_true", help="Salida JSON")

    p_eval = sub.add_parser(
        "evaluate-3c", help="Evaluar las cuatro consultas de etapa 3C con Ollama local"
    )
    p_eval.add_argument("--limit", type=int, default=20, help="Candidatos por consulta")
    p_eval.add_argument("--model", default=DEFAULT_GENERATION_MODEL)
    p_eval.add_argument("--json", action="store_true", help="Salida JSON completa")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    try:
        if args.command == "ingest":
            manifest = ingest_bibliography(force_rar=args.force_rar)
            if args.json:
                print(json.dumps(manifest, ensure_ascii=False, indent=2))
            else:
                _print_manifest(manifest)
            return 0

        if args.command == "stats":
            data = stats()
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                _print_stats(data)
            return 0

        if args.command == "search":
            results = search(
                args.query,
                limit=args.limit,
                doc_id=args.doc_id,
                page=args.page,
            )
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                _print_results(args.query, results)
            return 0

        if args.command == "verify":
            data = verify_index()
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print("OK" if data["ok"] else "FALLO")
                for name, value in data["checks"].items():
                    print(f" - {name}: {value}")
                for error in data["errors"]:
                    print(" - ERROR:", error)
            return 0 if data["ok"] else 1

        if args.command == "embed-build":
            def _progress(done, total):
                if not args.json:
                    print(f"\rEmbeddings: {done}/{total}", end="", flush=True)

            data = build_embeddings(
                backend=args.backend,
                model=args.model,
                base_url=args.ollama_url,
                batch_size=args.batch_size,
                limit=args.limit,
                progress=_progress,
            )
            if not args.json:
                print()
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print("Embeddings:", data["embeddings_db"])
                print("Chunks:", data["chunks"])
                print("Modelo:", data["model"])
                print("Backend:", data["backend"])
                print("Dimension:", data["dim"])
                print("Tiempo (s):", data["seconds"])
            return 0

        if args.command == "embed-stats":
            data = embeddings_stats()
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                print("Chunks:", data["chunks"])
                print("Dimensiones:", data["min_dim"], "-", data["max_dim"])
                for key, value in data["metadata"].items():
                    print(f" - {key}: {value}")
            return 0

        if args.command == "search-semantic":
            results = semantic_search(
                args.query,
                limit=args.limit,
                doc_id=args.doc_id,
                page=args.page,
                backend=args.backend,
                model=args.model,
                base_url=args.ollama_url,
            )
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                _print_results(args.query, results, mode="semantica")
            return 0

        if args.command == "search-hybrid":
            results = hybrid_search(
                args.query,
                limit=args.limit,
                doc_id=args.doc_id,
                page=args.page,
                backend=args.backend,
                model=args.model,
                base_url=args.ollama_url,
            )
            if args.json:
                print(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                _print_results(args.query, results, mode="hibrida")
            return 0

        if args.command == "ask":
            result = answer_question(
                args.question,
                limit=args.limit,
                model=args.model,
                base_url=args.ollama_url,
            )
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                _print_answer(result)
            return 0

        if args.command == "evaluate-3c":
            data = evaluate_stage_3c(model=args.model, limit=args.limit)
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            else:
                for record in data["records"]:
                    print("\nPregunta:", record["question"])
                    print("Resultado:", record["status"])
                    print("Respuesta:", record["answer"])
                    print("Tiempos:", json.dumps(record["timings"], ensure_ascii=False))
                    print("Aceptados:", len(record["accepted_evidence"]),
                          "Descartados:", len(record["discarded_evidence"]))
                    for ref in record["references"]:
                        print(f"  [{ref['id']}] {ref['document']} p.{ref['page']}")
            return 0
    except FileNotFoundError as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    except (RuntimeError, ValueError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
