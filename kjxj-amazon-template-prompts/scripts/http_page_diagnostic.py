#!/usr/bin/env python3
"""Collect last-resort Amazon page diagnostics without extracting products."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MARKERS = {
    "captcha": ("captcha", "robot check", "automated access"),
    "login": ("sign in", "login"),
    "service_unavailable": ("service unavailable", "503"),
}


def classify(status: int | None, body: str) -> tuple[str, str]:
    lower = body.lower()
    for page_status, markers in MARKERS.items():
        if any(marker in lower for marker in markers):
            return page_status, page_status
    if status == 503:
        return "service_unavailable", "HTTP 503"
    if status is not None and 200 <= status < 400:
        return "unknown", "页面未提供可验证商品卡片"
    return "failed", f"HTTP {status}" if status is not None else "请求失败"


def diagnose(url: str, timeout: int) -> dict[str, Any]:
    captured_at = datetime.now(timezone.utc).isoformat()
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            final_url = response.url
            body = response.read(200_000).decode("utf-8", errors="ignore")
    except HTTPError as exc:
        status, final_url = exc.code, exc.url
        body = exc.read(200_000).decode("utf-8", errors="ignore")
    except URLError as exc:
        return {"channel": "http_diagnostic", "captured_at": captured_at, "url": url, "final_url": url,
                "page_status": "failed", "status_code": None, "result_count": 0, "reason": str(exc.reason),
                "continue_to_next": False}
    page_status, reason = classify(status, body)
    return {"channel": "http_diagnostic", "captured_at": captured_at, "url": url, "final_url": final_url,
            "page_status": page_status, "status_code": status, "result_count": 0, "reason": reason,
            "continue_to_next": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="仅诊断 Amazon 页面，不提取竞品 ASIN")
    parser.add_argument("url", nargs="?")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        assert classify(503, "Sorry, service unavailable")[0] == "service_unavailable"
        assert classify(200, "Robot Check")[0] == "captcha"
        assert classify(200, "normal page")[0] == "unknown"
        print("self-test passed")
        return 0
    if not args.url:
        parser.error("需要 Amazon 页面 URL")
    print(json.dumps(diagnose(args.url, args.timeout), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
