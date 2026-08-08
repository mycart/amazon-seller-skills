#!/usr/bin/env python3
"""Fetch auditable Amazon page evidence and classify anti-automation responses."""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import html
import json
import re
import sys
import zlib
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


MARKETPLACE_DOMAINS = {
    "US": "www.amazon.com", "UK": "www.amazon.co.uk", "DE": "www.amazon.de",
    "FR": "www.amazon.fr", "IT": "www.amazon.it", "ES": "www.amazon.es",
    "JP": "www.amazon.co.jp", "CA": "www.amazon.ca", "AU": "www.amazon.com.au",
    "IN": "www.amazon.in", "MX": "www.amazon.com.mx", "BR": "www.amazon.com.br",
}
ASIN_RE = re.compile(r"^B0[A-Z0-9]{8}$")
STATIC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
}
CHALLENGE_MARKERS = {
    "automated_access": "automated access",
    "captcha": "captcha",
    "robot_check": "robot check",
    "validate_captcha": "/errors/validatecaptcha",
    "api_services_support": "api-services-support@amazon.com",
}


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def extract_title(page):
    match = re.search(r'<span[^>]+id=["\']productTitle["\'][^>]*>(.*?)</span>', page, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", match.group(1))).split())


def decode_page(response):
    body = response.read()
    headers = getattr(response, "headers", {})
    encoding = headers.get("Content-Encoding", "").casefold() if hasattr(headers, "get") else ""
    if encoding == "gzip":
        body = gzip.decompress(body)
    elif encoding == "deflate":
        body = zlib.decompress(body)
    return body.decode("utf-8", errors="replace")


def challenge_signals(page="", status_code=None):
    lowered = page.casefold()
    signals = [name for name, marker in CHALLENGE_MARKERS.items() if marker in lowered]
    if status_code in (429, 503):
        signals.append(f"http_{status_code}")
    return signals


def failure_summary(attempts):
    return "; ".join(
        item.get("failure_reason")
        or f"invalid response: status={item.get('status_code')} domain={item.get('domain')} "
        f"asin={item.get('parsed_asin')} title={item.get('title_state')} "
        f"category={item.get('failure_category')}"
        for item in attempts
    )


def fetch_one(asin, domain, opener=urlopen):
    attempts = []
    for path in (f"/dp/{asin}", f"/gp/product/{asin}"):
        url = f"https://{domain}{path}"
        try:
            request = Request(url, headers=STATIC_HEADERS)
            with opener(request, timeout=20) as response:
                final_url = response.geturl()
                status = getattr(response, "status", response.getcode())
                page = decode_page(response)
            final_domain = urlparse(final_url).netloc.casefold()
            parsed = re.search(r"/(?:dp|gp/product)/(B0[A-Z0-9]{8})", final_url, flags=re.IGNORECASE) or re.search(r"(?:asin|dp)=?(B0[A-Z0-9]{8})", page, flags=re.IGNORECASE)
            parsed_asin = parsed.group(1).upper() if parsed else ""
            title = extract_title(page)
            signals = challenge_signals(page, status)
            valid = 200 <= status < 300 and final_domain == domain and parsed_asin == asin and bool(title) and not signals
            attempt = {
                "transport": "http",
                "url": url,
                "status_code": status,
                "final_url": final_url,
                "domain": final_domain,
                "parsed_asin": parsed_asin,
                "title": title,
                "title_state": "present" if title else "empty",
                "challenge_signals": signals,
                "valid": valid,
            }
            if not valid:
                attempt["failure_category"] = "automation_challenge" if signals else "invalid_response"
            attempts.append(attempt)
            if valid:
                return {
                    "asin": asin, "status": "verified", "source": "http", "domain": domain,
                    "final_url": final_url, "title": title, "captured_at": now(), "attempts": attempts,
                }
        except HTTPError as exc:
            signals = challenge_signals(status_code=exc.code)
            attempts.append({
                "transport": "http", "url": url, "status_code": exc.code,
                "challenge_signals": signals, "failure_category": "automation_challenge" if signals else "http_error",
                "failure_reason": str(exc), "valid": False,
            })
        except (URLError, TimeoutError, OSError) as exc:
            attempts.append({
                "transport": "http", "url": url, "status_code": None, "challenge_signals": [],
                "failure_category": "network_error", "failure_reason": str(exc), "valid": False,
            })
    status = "needs_browser_evidence" if any(item.get("failure_category") == "automation_challenge" for item in attempts) else "failed"
    return {
        "asin": asin, "status": status, "domain": domain, "failure_reason": failure_summary(attempts),
        "captured_at": now(), "attempts": attempts,
    }


def collect_evidence(marketplace, primary_asin, competitor_asins=(), opener=urlopen):
    marketplace = marketplace.upper()
    domain = MARKETPLACE_DOMAINS.get(marketplace)
    if not domain:
        raise ValueError(f"unsupported marketplace: {marketplace}")
    for asin in (primary_asin, *competitor_asins):
        if not ASIN_RE.fullmatch(asin.upper()):
            raise ValueError(f"invalid ASIN: {asin}")
    primary = fetch_one(primary_asin.upper(), domain, opener)
    competitors = [fetch_one(asin.upper(), domain, opener) for asin in competitor_asins]
    status = "ready" if primary["status"] == "verified" else "needs_browser_evidence" if primary["status"] == "needs_browser_evidence" else "blocked"
    blocked_reason = "" if status in ("ready", "needs_browser_evidence") else "主 ASIN 页面证据门失败：未取得经站点、ASIN、状态码和非空标题校验的页面证据。"
    return {
        "marketplace": marketplace, "primary_asin": primary_asin.upper(), "primary": primary,
        "competitors": competitors, "status": status, "blocked_reason": blocked_reason,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--marketplace", required=True)
    parser.add_argument("--primary-asin", required=True)
    parser.add_argument("--competitor-asin", action="append", default=[])
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        evidence = collect_evidence(args.marketplace, args.primary_asin, args.competitor_asin)
    except ValueError as exc:
        parser.error(str(exc))
    Path(args.output).write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "output": args.output, "blocked_reason": evidence["blocked_reason"]}, ensure_ascii=False))
    if evidence["status"] == "blocked":
        sys.exit(2)


if __name__ == "__main__":
    main()
