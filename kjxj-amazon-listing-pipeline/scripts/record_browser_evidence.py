#!/usr/bin/env python3
"""Validate and append Chrome page observations to Amazon evidence JSON."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

from fetch_amazon_evidence import MARKETPLACE_DOMAINS


ASIN_RE = re.compile(r"^B0[A-Z0-9]{8}$")


def now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parsed_asin_from_url(url):
    match = re.search(r"/(?:dp|gp/product)/(B0[A-Z0-9]{8})", url, flags=re.IGNORECASE)
    return match.group(1).upper() if match else ""


def refresh_status(evidence):
    primary_status = evidence["primary"]["status"]
    evidence["status"] = "ready" if primary_status == "verified" else "blocked"
    evidence["blocked_reason"] = "" if primary_status == "verified" else "主 ASIN 页面证据门失败：未取得经站点、ASIN、页面状态和非空标题校验的页面证据。"


def record_browser_observation(evidence, asin, outcome, final_url="", title="", title_selector="#productTitle", challenge_signals=(), failure_reason="", captured_at=None):
    asin = asin.upper()
    expected_domain = MARKETPLACE_DOMAINS[evidence["marketplace"].upper()]
    records = [evidence["primary"], *evidence.get("competitors", [])]
    record = next((item for item in records if item.get("asin") == asin), None)
    if record is None:
        raise ValueError(f"ASIN is not present in evidence: {asin}")
    if record.get("status") != "needs_browser_evidence":
        raise ValueError(f"ASIN does not require browser evidence: {asin}")
    if outcome not in {"observed", "challenge", "unavailable"}:
        raise ValueError(f"invalid browser outcome: {outcome}")
    signals = list(dict.fromkeys(challenge_signals))
    parsed_asin = parsed_asin_from_url(final_url)
    domain = urlparse(final_url).netloc.casefold() if final_url else ""
    title = " ".join(title.split())
    valid = outcome == "observed" and title_selector == "#productTitle" and domain == expected_domain and parsed_asin == asin and bool(title) and not signals
    attempt = {
        "transport": "chrome", "url": f"https://{expected_domain}/dp/{asin}", "page_state": outcome,
        "final_url": final_url, "domain": domain, "parsed_asin": parsed_asin, "title": title, "title_selector": title_selector,
        "title_state": "present" if title else "empty", "challenge_signals": signals, "valid": valid,
        "captured_at": captured_at or now(),
    }
    if valid:
        record.update({
            "status": "verified", "source": "chrome", "domain": expected_domain, "final_url": final_url,
            "title": title, "captured_at": attempt["captured_at"], "failure_reason": "",
        })
    else:
        reason = failure_reason or (
            "Chrome unavailable" if outcome == "unavailable" else
            "Chrome page contains an automation challenge" if outcome == "challenge" or signals else
            f"invalid Chrome page: domain={domain} asin={parsed_asin} selector={title_selector} title={attempt['title_state']}"
        )
        attempt["failure_category"] = "automation_challenge" if outcome == "challenge" or signals else "browser_evidence_failed"
        attempt["failure_reason"] = reason
        record.update({"status": "failed", "failure_reason": reason, "captured_at": attempt["captured_at"]})
    record.setdefault("attempts", []).append(attempt)
    refresh_status(evidence)
    return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--asin", required=True)
    parser.add_argument("--outcome", required=True, choices=("observed", "challenge", "unavailable"))
    parser.add_argument("--final-url", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--title-selector", default="#productTitle")
    parser.add_argument("--challenge-signal", action="append", default=[])
    parser.add_argument("--failure-reason", default="")
    parser.add_argument("--captured-at", default="")
    args = parser.parse_args()
    evidence_path = Path(args.evidence)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    try:
        record_browser_observation(
            evidence, args.asin, args.outcome, args.final_url, args.title, args.title_selector,
            args.challenge_signal, args.failure_reason, args.captured_at or None,
        )
    except (KeyError, ValueError) as exc:
        parser.error(str(exc))
    evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "output": str(evidence_path)}, ensure_ascii=False))
    if evidence["status"] == "blocked":
        sys.exit(2)


if __name__ == "__main__":
    main()
