import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PPC = ROOT / "scripts" / "external_adapters" / "ppc_mode_a_adapter.py"
AUDIT = ROOT / "scripts" / "audit-external-dependencies.py"


def packet(label="CareCooo Kratzmatte", title="CareCooo Kratzmatte selbstklebend"):
    return {
        "mode": "A", "primary_asin": "B0GKDK191Q", "marketplace": "DE", "currency": "EUR",
        "financial": {
            "selling_price": {"value": 18, "source": "user_provided", "reason": "用户提供售价"},
            "monthly_ad_budget": {"value": 600, "source": "default", "reason": "默认月预算"},
            "break_even_acos": {"value": .4, "source": "default", "reason": "默认盈亏平衡 ACoS"},
            "conversion_rate": {"value": None, "source": "not_provided", "reason": "未提供转化率"},
        },
        "financial_defaults_applied": {"selling_price": {"used": False}, "monthly_ad_budget": {"used": True, "base_amount": 600, "base_currency": "EUR", "local_amount": 600}, "break_even_acos": {"used": True, "value": .4, "reason": "默认盈亏平衡 ACoS"}},
        "product_context": {"campaign_label": label, "recommended_2026_title": title},
        "keywords": [{"keyword": "kratzmatte selbstklebend", "ppc_eligible": True}], "keyword_pool": {"sha256": "a" * 64}, "competitor_asins": ["B0D4TPT9GW"],
    }


class ExternalAdapterTests(unittest.TestCase):
    def test_locked_external_skills_are_clean(self):
        completed = subprocess.run(["python3", str(AUDIT), "check"], text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_ppc_keeps_explicit_price_and_product_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); paths = {key: root / f"{key}.json" for key in ("packet", "request", "plan", "raw")}
            paths["packet"].write_text(json.dumps(packet(), ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(["python3", str(PPC), "run", "--packet", str(paths["packet"]), "--request", str(paths["request"]), "--plan", str(paths["plan"]), "--markdown", str(root / "plan.md"), "--raw-output", str(paths["raw"])], text=True, capture_output=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            plan = json.loads(paths["plan"].read_text(encoding="utf-8"))
            self.assertEqual(plan["financial_framework"]["selling_price"], 18)
            self.assertFalse(plan["financial_framework"]["defaults_applied"]["selling_price"]["used"])
            self.assertTrue(all(item["name"].startswith("CareCooo Kratzmatte - ") for item in plan["campaigns"]))
            self.assertNotIn("Katzenklo", json.dumps(plan, ensure_ascii=False))
            self.assertIn("execution_provenance", plan)

    def test_ppc_rejects_unverified_campaign_label(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / "packet.json"; source.write_text(json.dumps(packet(label="Katzenklo Schrank"), ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(["python3", str(PPC), "run", "--packet", str(source), "--request", str(root / "request.json"), "--plan", str(root / "plan.json"), "--markdown", str(root / "plan.md"), "--raw-output", str(root / "raw.md")], text=True, capture_output=True, check=False)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("固定类目名称", completed.stderr)


if __name__ == "__main__":
    unittest.main()
