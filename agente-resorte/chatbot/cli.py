"""CLI local para ingestar, consultar y verificar la bibliografia."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import config
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


def _print_results(query: str, results: list[dict]) -> None:
    print(f"Consulta: {query}")
    if not results:
        print("Sin resultados.")
        return
    for i, result in enumerate(results, 1):
        print(
            f"\n[{i}] {result['source_path']} p.{result['page']} "
            f"chunk {result['chunk_index']} score={result['score']:.3f}"
        )
        print("   ", result["snippet"].replace("\n", " "))


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
    except FileNotFoundError as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
