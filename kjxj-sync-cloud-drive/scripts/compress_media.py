#!/usr/bin/env python3
"""Create a confirmed-operation compression derivative. Never changes the source."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff"}


def run(command: list[str]) -> tuple[bool, str]:
    completed = subprocess.run(command, capture_output=True, text=True)
    return completed.returncode == 0, (completed.stderr or completed.stdout).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Compress one image or PDF into an explicit output path.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--image-quality", type=int, default=70)
    args = parser.parse_args()
    source, output = Path(args.source).expanduser(), Path(args.output).expanduser()
    result = {"source": str(source), "output": str(output), "ok": False, "errors": [], "warnings": []}
    if not source.is_file():
        result["errors"].append("source_not_found")
    elif output.exists():
        result["errors"].append("output_already_exists")
    elif output.parent.exists() is False:
        result["errors"].append("output_parent_not_found")
    if result["errors"]:
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 1

    suffix = source.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        if not shutil.which("sips"):
            result["errors"].append("sips_unavailable")
        else:
            target_format = "jpeg" if output.suffix.lower() in {".jpg", ".jpeg"} else "png"
            ok, message = run(["sips", "-s", "format", target_format, "-s", "formatOptions", str(args.image_quality), str(source), "--out", str(output)])
            if not ok: result["errors"].append(f"image_compression_failed: {message}")
    elif suffix == ".pdf":
        if shutil.which("qpdf"):
            ok, message = run(["qpdf", "--stream-data=compress", "--object-streams=generate", str(source), str(output)])
            if not ok: result["errors"].append(f"pdf_compression_failed: {message}")
        elif shutil.which("gs"):
            ok, message = run(["gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4", "-dPDFSETTINGS=/ebook", "-dNOPAUSE", "-dQUIET", "-dBATCH", f"-sOutputFile={output}", str(source)])
            if not ok: result["errors"].append(f"pdf_compression_failed: {message}")
        else:
            result["errors"].append("pdf_compressor_unavailable")
    else:
        result["errors"].append("unsupported_media_type")

    if output.exists():
        result["output_size_bytes"] = output.stat().st_size
        result["within_size_limit"] = output.stat().st_size <= MAX_BYTES
        if not result["within_size_limit"]: result["errors"].append("output_exceeds_10mb_limit")
    result["ok"] = not result["errors"]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
