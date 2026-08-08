import hashlib
import importlib.util
import json
import gzip
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError


SKILL = Path(__file__).resolve().parents[1]
FETCH_PATH = SKILL / "scripts" / "fetch_amazon_evidence.py"
BUILD_PATH = SKILL / "scripts" / "build_review_package.py"
SPEC = importlib.util.spec_from_file_location("fetch_amazon_evidence", FETCH_PATH)
FETCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FETCH)
sys.path.insert(0, str(SKILL / "scripts"))
RECORD_PATH = SKILL / "scripts" / "record_browser_evidence.py"
RECORD_SPEC = importlib.util.spec_from_file_location("record_browser_evidence", RECORD_PATH)
RECORD = importlib.util.module_from_spec(RECORD_SPEC)
RECORD_SPEC.loader.exec_module(RECORD)


class Response:
    status = 200

    def __init__(self, url, title="Verified Title"):
        self.url = url
        self.title = title

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self):
        return self.url

    def getcode(self):
        return self.status

    def read(self):
        return f'<span id="productTitle">{self.title}</span>'.encode()


class EvidenceGateTests(unittest.TestCase):
    def test_uk_primary_uses_uk_domain_and_accepts_non_empty_title(self):
        def opener(request, timeout):
            self.assertEqual(request.full_url, "https://www.amazon.co.uk/dp/B0ABCDEFG1")
            return Response(request.full_url)

        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=opener)
        self.assertEqual(evidence["status"], "ready")
        self.assertEqual(evidence["primary"]["domain"], "www.amazon.co.uk")
        self.assertEqual(evidence["primary"]["title"], "Verified Title")

    def test_gzip_static_response_is_decoded_before_title_validation(self):
        class GzipResponse(Response):
            headers = {"Content-Encoding": "gzip"}

            def read(self):
                return gzip.compress(b'<span id="productTitle">Compressed Title</span>')

        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=lambda request, timeout: GzipResponse(request.full_url))
        self.assertEqual(evidence["status"], "ready")
        self.assertEqual(evidence["primary"]["title"], "Compressed Title")

    def test_empty_primary_title_blocks_workflow(self):
        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=lambda request, timeout: Response(request.full_url, ""))
        self.assertEqual(evidence["status"], "blocked")
        self.assertEqual(evidence["primary"]["status"], "failed")
        self.assertEqual(len(evidence["primary"]["attempts"]), 2)

    def test_primary_http_failure_blocks_workflow(self):
        def opener(request, timeout):
            raise HTTPError(request.full_url, 503, "unavailable", None, None)

        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=opener)
        self.assertEqual(evidence["status"], "needs_browser_evidence")
        self.assertIn("503", evidence["primary"]["failure_reason"])
        self.assertEqual(evidence["primary"]["attempts"][0]["failure_category"], "automation_challenge")

    def test_wrong_final_domain_blocks_workflow(self):
        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=lambda request, timeout: Response("https://www.amazon.com/dp/B0ABCDEFG1"))
        self.assertEqual(evidence["status"], "blocked")
        self.assertIn("domain=www.amazon.com", evidence["primary"]["failure_reason"])

    def test_wrong_parsed_asin_blocks_workflow(self):
        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=lambda request, timeout: Response("https://www.amazon.co.uk/dp/B0WRONG001"))
        self.assertEqual(evidence["status"], "blocked")
        self.assertIn("asin=B0WRONG001", evidence["primary"]["failure_reason"])

    def test_competitor_failure_is_a_non_blocking_gap(self):
        def opener(request, timeout):
            if "B0COMPET01" in request.full_url:
                raise HTTPError(request.full_url, 503, "unavailable", None, None)
            return Response(request.full_url)

        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", ["B0COMPET01"], opener=opener)
        self.assertEqual(evidence["status"], "ready")
        self.assertEqual(evidence["competitors"][0]["status"], "needs_browser_evidence")

    def test_captcha_page_requires_browser_evidence_and_keeps_attempts(self):
        class ChallengeResponse(Response):
            def read(self):
                return b"<title>Amazon.co.uk</title>To discuss automated access, contact us. Captcha"

        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=lambda request, timeout: ChallengeResponse(request.full_url, ""))
        self.assertEqual(evidence["status"], "needs_browser_evidence")
        self.assertEqual(len(evidence["primary"]["attempts"]), 2)
        self.assertIn("automated_access", evidence["primary"]["attempts"][0]["challenge_signals"])
        self.assertIn("captcha", evidence["primary"]["attempts"][0]["challenge_signals"])

    def test_browser_evidence_verifies_primary_after_static_challenge(self):
        class ChallengeResponse(Response):
            def read(self):
                return b"automated access captcha"

        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=lambda request, timeout: ChallengeResponse(request.full_url, ""))
        RECORD.record_browser_observation(
            evidence, "B0ABCDEFG1", "observed", "https://www.amazon.co.uk/dp/B0ABCDEFG1",
            "Chrome Verified Title",
        )
        self.assertEqual(evidence["status"], "ready")
        self.assertEqual(evidence["primary"]["status"], "verified")
        self.assertEqual(evidence["primary"]["source"], "chrome")
        self.assertEqual(evidence["primary"]["attempts"][-1]["transport"], "chrome")
        self.assertEqual(evidence["primary"]["attempts"][-1]["title_selector"], "#productTitle")

    def test_browser_evidence_rejects_a_non_product_title_selector(self):
        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=lambda request, timeout: Response(request.full_url, ""))
        evidence["primary"]["status"] = "needs_browser_evidence"
        RECORD.record_browser_observation(
            evidence, "B0ABCDEFG1", "observed", "https://www.amazon.co.uk/dp/B0ABCDEFG1",
            "Browser Tab Title", "title",
        )
        self.assertEqual(evidence["status"], "blocked")
        self.assertEqual(evidence["primary"]["attempts"][-1]["failure_category"], "browser_evidence_failed")

    def test_browser_wrong_asin_or_challenge_blocks_primary(self):
        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=lambda request, timeout: Response(request.full_url, ""))
        evidence["primary"]["status"] = "needs_browser_evidence"
        RECORD.record_browser_observation(
            evidence, "B0ABCDEFG1", "challenge", "https://www.amazon.co.uk/dp/B0ABCDEFG1",
            "", challenge_signals=["captcha"],
        )
        self.assertEqual(evidence["status"], "blocked")
        self.assertEqual(evidence["primary"]["status"], "failed")
        self.assertEqual(evidence["primary"]["attempts"][-1]["failure_category"], "automation_challenge")

    def test_browser_wrong_asin_blocks_primary(self):
        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", opener=lambda request, timeout: Response(request.full_url, ""))
        evidence["primary"]["status"] = "needs_browser_evidence"
        RECORD.record_browser_observation(
            evidence, "B0ABCDEFG1", "observed", "https://www.amazon.co.uk/dp/B0WRONG001",
            "Wrong ASIN Title",
        )
        self.assertEqual(evidence["status"], "blocked")
        self.assertEqual(evidence["primary"]["attempts"][-1]["failure_category"], "browser_evidence_failed")

    def test_browser_competitor_failure_does_not_block_verified_primary(self):
        def opener(request, timeout):
            if "B0COMPET01" in request.full_url:
                raise HTTPError(request.full_url, 503, "unavailable", None, None)
            return Response(request.full_url)

        evidence = FETCH.collect_evidence("UK", "B0ABCDEFG1", ["B0COMPET01"], opener=opener)
        RECORD.record_browser_observation(evidence, "B0COMPET01", "unavailable", failure_reason="Chrome unavailable")
        self.assertEqual(evidence["status"], "ready")
        self.assertEqual(evidence["competitors"][0]["status"], "failed")


class ReviewPackageTests(unittest.TestCase):
    def write(self, root, name, content):
        path = root / name
        path.write_text(content, encoding="utf-8")
        return path

    def fixture_paths(self, root):
        listing = self.write(root, "listing.md", """### Title

Verified Cat Mat

### Bullet Points

1. First bullet
2. Second bullet
3. Third bullet
4. Fourth bullet
5. Fifth bullet

### Product Description

Verified description.

### Backend Search Terms

cat mat sisal
""")
        title = self.write(root, "title.md", """### Option 1

Title: Short Cat Mat

Item Highlights: Durable sisal
""")
        ppc = self.write(root, "ppc.md", """## Campaign 1: Exact

Positive Keywords
- cat mat
Negative Keywords
- free
""")
        qa = "\n\n".join(f"Q{i}. Question {i}?\n\nA{i}. Answer {i}.\n\n仅供审核：问题 {i} 的审核翻译。" for i in range(1, 9))
        rufus = self.write(root, "rufus.md", qa + "\n")
        plan = self.write(root, "plan.json", json.dumps({"actions": [{"asin": "B0ABCDEFG1", "marketplace": "UK", "status": "ready", "rows": [7], "sheet": "Template", "fields": {"title": "Short Cat Mat", "item_highlight": "Durable sisal", "title_mode": "短标题方案 1"}}]}))
        evidence = self.write(root, "evidence.json", json.dumps({"primary_asin": "B0ABCDEFG1", "primary": {"asin": "B0ABCDEFG1", "status": "verified", "domain": "www.amazon.co.uk", "title": "Verified Cat Mat", "final_url": "https://www.amazon.co.uk/dp/B0ABCDEFG1", "captured_at": "2026-08-08T00:00:00+00:00"}, "competitors": [{"asin": "B0COMPET01", "status": "failed", "failure_reason": "HTTP 503"}]}))
        source_paths = [listing, title, ppc, rufus]
        frozen = self.write(root, "frozen.json", json.dumps({str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}))
        return listing, title, ppc, rufus, plan, evidence, frozen

    def run_builder(self, root, paths):
        listing, title, ppc, rufus, plan, evidence, frozen = paths
        return subprocess.run(["python3", str(BUILD_PATH), "--listing", str(listing), "--title", str(title), "--ppc", str(ppc), "--rufus", str(rufus), "--plan", str(plan), "--evidence", str(evidence), "--frozen-source-manifest", str(frozen), "--base", "test", "--output-dir", str(root / "out")], capture_output=True, text=True)

    def variant_fixture_paths(self, root):
        listing_white = self.write(root, "white-listing.md", """### Title

White Cat Mat

### Bullet Points

1. White first bullet
2. White second bullet
3. White third bullet
4. White fourth bullet
5. White fifth bullet

### Product Description

White description.

### Backend Search Terms

white cat mat
""")
        title_white = self.write(root, "white-title.md", """### Option 1

Title: White Cat Mat

Item Highlights: White durable sisal
""")
        listing_natural = self.write(root, "natural-listing.md", """### Title

Natural Cat Mat

### Bullet Points

1. Natural first bullet
2. Natural second bullet
3. Natural third bullet
4. Natural fourth bullet
5. Natural fifth bullet

### Product Description

Natural description.

### Backend Search Terms

natural cat mat
""")
        title_natural = self.write(root, "natural-title.md", """### Option 1

Title: Natural Cat Mat

Item Highlights: Natural durable sisal
""")
        ppc = self.write(root, "ppc.md", """## Campaign 1: Exact

Positive Keywords
- cat mat
Negative Keywords
- free
""")
        qa = "\n\n".join(f"Q{i}. Question {i}?\n\nA{i}. Answer {i}.\n\n仅供审核：问题 {i} 的审核翻译。" for i in range(1, 9))
        rufus = self.write(root, "rufus.md", qa + "\n")
        actions = [
            {"asin": "B0WHITE001", "marketplace": "UK", "status": "ready", "rows": [17], "sheet": "Template", "variant": {"color": "White", "dimensions": "60 x 40 cm"}, "preflight": {"product_id_type": "ASIN"}, "fields": {"title": "White Cat Mat", "item_highlight": "White durable sisal", "title_mode": "Option 1"}},
            {"asin": "B0NATURAL1", "marketplace": "UK", "status": "ready", "rows": [18], "sheet": "Template", "variant": {"color": "Naturally", "dimensions": "60 x 40 cm"}, "preflight": {"product_id_type": "ASIN"}, "fields": {"title": "Natural Cat Mat", "item_highlight": "Natural durable sisal", "title_mode": "Option 1"}},
        ]
        plan = self.write(root, "plan.json", json.dumps({"actions": actions}))
        evidence = self.write(root, "evidence.json", json.dumps({"primary_asin": "B0WHITE001", "primary": {"asin": "B0WHITE001", "status": "verified", "domain": "www.amazon.co.uk", "title": "White Cat Mat", "final_url": "https://www.amazon.co.uk/dp/B0WHITE001", "captured_at": "2026-08-08T00:00:00+00:00"}, "competitors": []}))
        sources = [listing_white, title_white, listing_natural, title_natural, ppc, rufus]
        frozen = self.write(root, "frozen.json", json.dumps({str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}))
        variant_sources = self.write(root, "variants.json", json.dumps({
            "B0WHITE001": {"asin": "B0WHITE001", "marketplace": "UK", "listing": str(listing_white), "title": str(title_white), "variant": {"color": "White", "dimensions": "60 x 40 cm"}, "evidence": {"asin": "B0WHITE001", "status": "verified"}},
            "B0NATURAL1": {"asin": "B0NATURAL1", "marketplace": "UK", "listing": str(listing_natural), "title": str(title_natural), "variant": {"color": "Naturally", "dimensions": "60 x 40 cm"}, "evidence": {"asin": "B0NATURAL1", "status": "verified"}},
        }))
        return ppc, rufus, plan, evidence, frozen, variant_sources

    def run_variant_builder(self, root, paths):
        ppc, rufus, plan, evidence, frozen, variants = paths
        return subprocess.run(["python3", str(BUILD_PATH), "--variant-sources", str(variants), "--ppc", str(ppc), "--rufus", str(rufus), "--plan", str(plan), "--evidence", str(evidence), "--frozen-source-manifest", str(frozen), "--base", "variants", "--output-dir", str(root / "out")], capture_output=True, text=True)

    def test_summary_contains_all_required_audit_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = self.run_builder(root, self.fixture_paths(root))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = (root / "out" / "test-chinese-summary-review.md").read_text(encoding="utf-8")
            for value in ("Verified Cat Mat", "First bullet", "Verified description.", "cat mat sisal", "Short Cat Mat", "Durable sisal", "Campaign 1: Exact", "PPC 关键词复制区", "Q8. Question 8?", "仅供审核：问题 8 的审核翻译。", "HTTP 503"):
                self.assertIn(value, summary)

    def test_missing_listing_field_produces_no_review_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.fixture_paths(root)
            paths[0].write_text("### Title\n\nOnly title\n", encoding="utf-8")
            completed = self.run_builder(root, paths)
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((root / "out" / "test-sync-review.md").exists())

    def test_changed_frozen_source_checksum_blocks_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = self.fixture_paths(root)
            paths[2].write_text(paths[2].read_text(encoding="utf-8") + "\nChanged", encoding="utf-8")
            completed = self.run_builder(root, paths)
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse((root / "out" / "test-sync-review.md").exists())

    def test_variant_summary_contains_each_asin_with_its_own_listing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            completed = self.run_variant_builder(root, self.variant_fixture_paths(root))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            summary = (root / "out" / "variants-chinese-summary-review.md").read_text(encoding="utf-8")
            self.assertIn("SKU 变体 Listing: B0WHITE001", summary)
            self.assertIn("SKU 变体 Listing: B0NATURAL1", summary)
            self.assertIn("White Cat Mat", summary)
            self.assertIn("Natural Cat Mat", summary)
            self.assertIn("- color: White", summary)
            self.assertIn("- color: Naturally", summary)

    def test_variant_builder_blocks_missing_or_unverified_action_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = list(self.variant_fixture_paths(root))
            variants = json.loads(paths[-1].read_text(encoding="utf-8"))
            del variants["B0NATURAL1"]
            paths[-1].write_text(json.dumps(variants), encoding="utf-8")
            completed = self.run_variant_builder(root, paths)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("missing verified variant sources", completed.stderr)

            paths = list(self.variant_fixture_paths(root))
            variants = json.loads(paths[-1].read_text(encoding="utf-8"))
            variants["B0NATURAL1"]["evidence"]["status"] = "failed"
            paths[-1].write_text(json.dumps(variants), encoding="utf-8")
            completed = self.run_variant_builder(root, paths)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("lacks verified page evidence", completed.stderr)

    def test_variant_builder_blocks_variant_preflight_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = list(self.variant_fixture_paths(root))
            plan = json.loads(paths[2].read_text(encoding="utf-8"))
            plan["actions"][1]["variant"]["color"] = "White"
            paths[2].write_text(json.dumps(plan), encoding="utf-8")
            completed = self.run_variant_builder(root, paths)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("variant conflict for B0NATURAL1: color", completed.stderr)


if __name__ == "__main__":
    unittest.main()
