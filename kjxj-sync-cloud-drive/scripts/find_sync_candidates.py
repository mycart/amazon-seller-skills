#!/usr/bin/env python3
"""Read-only filename and workbook candidate finder for cloud-drive sync."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

EXCLUDED_NAMES = {"Icon", ".DS_Store"}
DEFAULT_EXTENSIONS = {".xlsx", ".xls", ".csv", ".tsv"}


def score(path: Path, terms: list[str]) -> int:
    haystack = str(path).casefold()
    return sum(1 for term in terms if term.casefold() in haystack)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only cloud-drive candidate search.")
    parser.add_argument("--root", required=True, help="Cloud-drive root directory.")
    parser.add_argument("--query", required=True, help="Topic, company, or filename keywords.")
    parser.add_argument("--mode", choices=("files", "workbooks"), default="files")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    root = Path(args.root).expanduser()
    terms = [part for part in args.query.replace("_", " ").split() if part]
    result = {"root": str(root), "query": args.query, "mode": args.mode, "candidates": [], "errors": []}
    if not root.is_dir():
        result["errors"].append("cloud_drive_root_not_found")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    candidates = []
    for path in root.rglob("*"):
        if not path.is_file() or path.name in EXCLUDED_NAMES:
            continue
        if args.mode == "workbooks" and path.suffix.lower() not in DEFAULT_EXTENSIONS:
            continue
        candidate_score = score(path, terms)
        if candidate_score:
            candidates.append((candidate_score, path))
    for candidate_score, path in sorted(candidates, key=lambda item: (-item[0], str(item[1])))[: args.limit]:
        result["candidates"].append(
            {"path": str(path), "score": candidate_score, "size_bytes": path.stat().st_size}
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
