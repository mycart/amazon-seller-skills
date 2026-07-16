#!/usr/bin/env python3
"""Read-only preflight checks for kjxj-sync-cloud-drive."""

from __future__ import annotations

import argparse
import hashlib
import mimetypes
import json
from pathlib import Path


MAX_BYTES = 10 * 1024 * 1024
COMPRESSIBLE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".pdf"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_result(source: Path, target: Path | None, include_hash: bool) -> dict:
    result: dict = {
        "ok": False,
        "limit_bytes": MAX_BYTES,
        "source": str(source),
        "source_exists": source.exists(),
        "source_is_file": source.is_file() if source.exists() else False,
        "target": str(target) if target else None,
        "target_exists": target.exists() if target else None,
        "target_parent_exists": target.parent.exists() if target else None,
        "target_conflict": target.exists() if target else None,
        "errors": [],
        "warnings": [],
    }

    if not result["source_exists"]:
        result["errors"].append("source_not_found")
        return result

    if not result["source_is_file"]:
        result["errors"].append("source_is_not_file")
        return result

    size = source.stat().st_size
    guessed_mime, _ = mimetypes.guess_type(source.name)
    result["source_size_bytes"] = size
    result["source_size_mb"] = round(size / (1024 * 1024), 4)
    result["within_size_limit"] = size <= MAX_BYTES
    result["source_suffix"] = source.suffix.lower()
    result["source_mime_type"] = guessed_mime
    result["compression_supported"] = source.suffix.lower() in COMPRESSIBLE_SUFFIXES

    if size > MAX_BYTES:
        result["errors"].append("source_exceeds_10mb_limit")

    if target and not target.parent.exists():
        result["warnings"].append("target_parent_missing")

    if target and target.exists():
        result["warnings"].append("target_exists_requires_user_review")

    if include_hash and size <= MAX_BYTES:
        result["source_sha256"] = sha256_file(source)

    result["ok"] = not result["errors"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only file sync preflight check. Does not copy, overwrite, create directories, or edit files."
    )
    parser.add_argument("--source", required=True, help="Absolute or relative source file path.")
    parser.add_argument("--target", help="Optional expected target file path.")
    parser.add_argument("--hash", action="store_true", help="Include SHA-256 for files within the 10 MB limit.")
    args = parser.parse_args()

    source = Path(args.source).expanduser()
    target = Path(args.target).expanduser() if args.target else None
    result = build_result(source, target, args.hash)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
