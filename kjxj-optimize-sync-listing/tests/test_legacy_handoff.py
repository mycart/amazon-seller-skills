import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module(
    "legacy_handoff_validator", ROOT / "scripts" / "validate-legacy-handoff.py"
)
class LegacyHandoffTests(unittest.TestCase):
    @staticmethod
    def validate_archived(report, artifact=None):
        return VALIDATOR.validate_report(
            report,
            artifact,
            allow_legacy_title_method=True,
        )

    def test_non_pet_hard_spec_precedes_keyword_only_priority(self):
        portable_blender_phrase = {
            "keyword_refs": ["KW-USB-C"],
            "selling_point_refs": [],
        }
        priority = VALIDATOR.expected_priority(
            portable_blender_phrase,
            {"specification", "compatibility"},
        )
        self.assertEqual(priority, "verified_spec_or_differentiator")

    def report(self) -> dict:
        manifest = {
            section: {
                "provided": True,
                "status": "used",
                "note": f"已处理德国猫抓垫输入：{section}",
            }
            for section in VALIDATOR.INPUT_SECTIONS
        }
        manifest["marketplace_language_tone"]["data"] = {
            "marketplace": "DE",
            "language": "de_DE",
            "tone": "Professional",
        }
        manifest["asin_target"]["data"] = {"asin": "B0GKDK191Q"}
        manifest["core_keywords"]["data"] = ["kratzmatte selbstklebend"]
        manifest["listing_eligible_keywords"]["data"] = [
            {"keyword": "kratzmatte selbstklebend", "metrics": {"search_volume": 1000}},
            {"keyword": "kratzschutz sofa", "metrics": {"search_volume": 500}},
        ]
        legacy_listing = {
            "title": (
                "CareCooo Kratzmatte selbstklebend aus dickem Sisal, starke Haftung "
                "und rutschfest, schützt Sofa und Möbel, Weiß, 60 x 40 cm"
            ),
            "bullets": [
                "DICK UND ABRIEBFEST — Die Kratzmatte selbstklebend aus Sisal hält täglichem Kratzen stand.",
                "SCHÜTZT SOFA UND MÖBEL — Deckt beanspruchte Flächen ab und bietet Katzen eine geeignete Kratzfläche.",
                "STARKE HAFTUNG — Die selbstklebende Rückseite lässt sich fest auf geeigneten glatten Flächen anbringen.",
                "RUTSCHFESTE NUTZUNG — Die haftende Unterseite hält die Katzen Kratzmatte beim Kratzen in Position.",
                "LEICHT ZU REINIGEN — Lose Haare und Staub lassen sich von der Oberfläche einfach entfernen.",
            ],
            "description": (
                "Diese selbstklebende Kratzmatte schützt beanspruchte Bereiche an Sofa, Wand und Möbeln. "
                "Der dicke Sisalstoff ist abriebfest, die stark haftende Rückseite vermindert Verrutschen. "
                "Die Oberfläche lässt sich leicht von Haaren und Staub reinigen. Größe: 60 x 40 cm, Farbe: Weiß."
            ),
            "backend_search_terms": (
                "kratzmatte selbstklebend kratzschutz sofa katzen kratzteppich sisal möbelschutz"
            ),
        }
        phrase_analysis = [
            {
                "id": "RP-01", "source_text": "CareCooo", "normalized_text": "carecooo",
                "source_order": 1, "roles": ["brand"], "keyword_refs": [],
                "selling_point_refs": [], "fact_refs": ["FACT-BRAND"],
                "evidence_status": "verified", "priority": "identity",
            },
            {
                "id": "RP-02", "source_text": "Kratzmatte", "normalized_text": "kratzmatte",
                "source_order": 2, "roles": ["core_product"], "keyword_refs": ["KW-001"],
                "selling_point_refs": [], "fact_refs": ["FACT-PRODUCT"],
                "evidence_status": "verified", "priority": "identity",
            },
            {
                "id": "RP-03", "source_text": "selbstklebend", "normalized_text": "selbstklebend",
                "source_order": 3, "roles": ["installation"], "keyword_refs": ["KW-001"],
                "selling_point_refs": ["SP-HAFTUNG"], "fact_refs": ["FACT-ADHESIVE"],
                "evidence_status": "verified", "priority": "dual_value",
            },
            {
                "id": "RP-04", "source_text": "aus dickem Sisal", "normalized_text": "aus dickem sisal",
                "source_order": 4, "roles": ["material"], "keyword_refs": ["KW-SISAL"],
                "selling_point_refs": ["SP-DICKE"], "fact_refs": ["FACT-SISAL"],
                "evidence_status": "verified", "priority": "dual_value",
            },
            {
                "id": "RP-05", "source_text": "starke Haftung", "normalized_text": "starke haftung",
                "source_order": 5, "roles": ["function"], "keyword_refs": [],
                "selling_point_refs": ["SP-HAFTUNG"], "fact_refs": ["FACT-ADHESIVE"],
                "evidence_status": "verified", "priority": "selling_point_only",
            },
            {
                "id": "RP-06", "source_text": "und rutschfest", "normalized_text": "und rutschfest",
                "source_order": 6, "roles": ["function"], "keyword_refs": ["KW-RUTSCHFEST"],
                "selling_point_refs": ["SP-RUTSCHFEST"], "fact_refs": ["FACT-NONSLIP"],
                "evidence_status": "verified", "priority": "dual_value",
            },
            {
                "id": "RP-07", "source_text": "schützt Sofa und Möbel",
                "normalized_text": "schützt sofa und möbel", "source_order": 7,
                "roles": ["benefit", "use_case"], "keyword_refs": ["KW-SOFASCHUTZ"],
                "selling_point_refs": ["SP-MÖBELSCHUTZ"], "fact_refs": ["FACT-FURNITURE"],
                "evidence_status": "verified", "priority": "dual_value",
            },
            {
                "id": "RP-08", "source_text": "Weiß", "normalized_text": "weiß",
                "source_order": 8, "roles": ["sku_attribute"], "keyword_refs": [],
                "selling_point_refs": [], "fact_refs": ["FACT-COLOR"],
                "evidence_status": "verified", "priority": "sku_attribute",
            },
            {
                "id": "RP-09", "source_text": "60 x 40 cm", "normalized_text": "60 x 40 cm",
                "source_order": 9, "roles": ["sku_attribute", "specification"],
                "keyword_refs": [], "selling_point_refs": [], "fact_refs": ["FACT-SIZE"],
                "evidence_status": "verified", "priority": "sku_attribute",
            },
        ]

        def allocations(specs):
            result = []
            for phrase in phrase_analysis:
                phrase_id = phrase["id"]
                placement, realization, reuse_type = specs[phrase_id]
                result.append({
                    "phrase_id": phrase_id,
                    "placement": placement,
                    "realization": realization,
                    "reuse_type": reuse_type,
                    "reason_code": "retained" if placement != "omitted" else "character_limit",
                    "reason": "沿用旧标题中的已验证表达" if placement != "omitted" else "受字符限制迁移或省略",
                })
            return result

        common_components = {
            "brand": "CareCooo", "core_product_phrase": "Kratzmatte",
            "differentiator": "", "sku_attributes": ["Weiß", "60 x 40 cm"],
        }
        options = [
            {
                "option": 1, "rank": 1, "status": "recommended_for_current_upload",
                "title": "CareCooo Kratzmatte Sisal 60x40cm, selbstklebend, rutschfest, Weiß",
                "item_highlights": "Starke Haftung, schützt Sofa und Möbel, abriebfest, für Katzen",
                "title_components": copy.deepcopy(common_components),
                "sku_attribute_placement": "title",
                "reference_phrase_allocation": allocations({
                    "RP-01": ("title", "CareCooo", "verbatim"),
                    "RP-02": ("title", "Kratzmatte", "verbatim"),
                    "RP-03": ("title", "selbstklebend", "verbatim"),
                    "RP-04": ("title", "Sisal", "controlled_rewrite"),
                    "RP-05": ("item_highlights", "Starke Haftung", "normalized"),
                    "RP-06": ("title", "rutschfest", "controlled_rewrite"),
                    "RP-07": ("item_highlights", "schützt Sofa und Möbel", "verbatim"),
                    "RP-08": ("title", "Weiß", "verbatim"),
                    "RP-09": ("title", "60x40cm", "normalized"),
                }),
                "additional_verified_phrases": [
                    {"text": "abriebfest", "placement": "item_highlights", "fact_refs": ["FACT-ABRASION"],
                     "keyword_refs": [], "selling_point_refs": ["SP-DICKE"], "reason": "用户卖点明确支持耐磨表达"},
                    {"text": "für Katzen", "placement": "item_highlights", "fact_refs": ["FACT-AUDIENCE"],
                     "keyword_refs": ["KW-KATZEN"], "selling_point_refs": [], "reason": "已验证Listing明确适用对象"},
                ],
            },
            {
                "option": 2, "rank": 2, "status": "alternate",
                "title": "CareCooo Kratzmatte selbstklebend aus Sisal, Weiß, 60 x 40 cm",
                "item_highlights": "Starke Haftung, rutschfest, schützt Sofa und Möbel",
                "title_components": copy.deepcopy(common_components),
                "sku_attribute_placement": "title",
                "reference_phrase_allocation": allocations({
                    "RP-01": ("title", "CareCooo", "verbatim"),
                    "RP-02": ("title", "Kratzmatte", "verbatim"),
                    "RP-03": ("title", "selbstklebend", "verbatim"),
                    "RP-04": ("title", "aus Sisal", "controlled_rewrite"),
                    "RP-05": ("item_highlights", "Starke Haftung", "normalized"),
                    "RP-06": ("item_highlights", "rutschfest", "controlled_rewrite"),
                    "RP-07": ("item_highlights", "schützt Sofa und Möbel", "verbatim"),
                    "RP-08": ("title", "Weiß", "verbatim"),
                    "RP-09": ("title", "60 x 40 cm", "verbatim"),
                }),
                "additional_verified_phrases": [],
            },
            {
                "option": 3, "rank": 3, "status": "alternate",
                "title": "CareCooo Kratzmatte, Weiß, 60 x 40 cm, Sisal, rutschfest",
                "item_highlights": "Selbstklebend, starke Haftung, schützt Sofa und Möbel",
                "title_components": copy.deepcopy(common_components),
                "sku_attribute_placement": "title",
                "reference_phrase_allocation": allocations({
                    "RP-01": ("title", "CareCooo", "verbatim"),
                    "RP-02": ("title", "Kratzmatte", "verbatim"),
                    "RP-03": ("item_highlights", "Selbstklebend", "normalized"),
                    "RP-04": ("title", "Sisal", "controlled_rewrite"),
                    "RP-05": ("item_highlights", "starke Haftung", "verbatim"),
                    "RP-06": ("title", "rutschfest", "controlled_rewrite"),
                    "RP-07": ("item_highlights", "schützt Sofa und Möbel", "verbatim"),
                    "RP-08": ("title", "Weiß", "verbatim"),
                    "RP-09": ("title", "60 x 40 cm", "verbatim"),
                }),
                "additional_verified_phrases": [],
            },
        ]
        return {
            "asin": "B0GKDK191Q",
            "mode": "B",
            "marketplace": "DE",
            "brand": "CareCooo",
            "generation_sequence": [
                "evidence_collection",
                "legacy_listing",
                "title_options_2026",
            ],
            "listing_generation_source": "amazon-listing-optimization",
            "legacy_generation": {
                "source_skill": "amazon-listing-optimization",
                "source_skill_path": (
                    "/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md"
                ),
                "source_skill_sha256": VALIDATOR.file_sha256(
                    Path("/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md")
                ),
                "artifact_path": "/tmp/legacy-listing-result-B0GKDK191Q.json",
                "invocation_id": "INV-B0GKDK191Q-20260730T100000",
                "started_at": "2026-07-30T09:59:00+08:00",
                "request_path": "/tmp/legacy-listing-request-B0GKDK191Q.json",
                "request_sha256": "0" * 64,
                "raw_output_path": "/tmp/legacy-listing-raw-output-B0GKDK191Q.md",
                "raw_output_sha256": "0" * 64,
                "mode": "B",
                "status": "complete",
                "completed_at": "2026-07-30T10:00:00+08:00",
                "input_manifest": manifest,
                "legacy_listing": legacy_listing,
                "keyword_priority": {
                    "primary": ["kratzmatte selbstklebend"],
                    "secondary": ["kratzschutz sofa"],
                    "tertiary": ["kratzteppich katze"],
                    "backend": [],
                },
                "keyword_coverage": [],
                "keyword_gaps": [],
                "limitations": [],
            },
            "listing": copy.deepcopy(legacy_listing),
            "title_options_generation": {
                "started_at": "2026-07-30T10:01:00+08:00",
                "reference_title": legacy_listing["title"],
                "method": "legacy_reference_phrase_allocation_v1",
                "reference_phrase_analysis": phrase_analysis,
            },
            "title_options_2026": options,
            "diagnostic": {},
        }

    def artifact(self, report: dict) -> dict:
        legacy = report["legacy_generation"]
        return {
            key: copy.deepcopy(legacy[key])
            for key in (
                "source_skill",
                "source_skill_path",
                "source_skill_sha256",
                "invocation_id",
                "started_at",
                "request_path",
                "request_sha256",
                "raw_output_path",
                "raw_output_sha256",
                "mode",
                "status",
                "completed_at",
                "input_manifest",
                "legacy_listing",
                "keyword_priority",
                "keyword_coverage",
                "keyword_gaps",
                "limitations",
            )
        }

    def test_german_cat_mat_handoff_uses_all_input_sections(self):
        report = self.report()
        result = self.validate_archived(report)
        self.assertTrue(result["ok"], result["errors"])
        self.assertIn("kratzmatte selbstklebend", report["legacy_generation"]["legacy_listing"]["title"].casefold())
        self.assertTrue(all(item["provided"] for item in report["legacy_generation"]["input_manifest"].values()))
        self.assertEqual(
            set(report["legacy_generation"]["input_manifest"]),
            set(VALIDATOR.INPUT_SECTIONS),
        )
        self.assertEqual(
            report["legacy_generation"]["input_manifest"]["asin_target"]["data"],
            {"asin": "B0GKDK191Q"},
        )
        self.assertTrue(any("SOFA UND MÖBEL" in bullet for bullet in report["listing"]["bullets"]))

    def test_missing_manifest_and_listing_mismatch_are_blocked(self):
        report = self.report()
        del report["legacy_generation"]["input_manifest"]["listing_eligible_keywords"]
        report["listing"]["title"] = "Handwritten short title"
        result = self.validate_archived(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("listing_eligible_keywords" in error for error in result["errors"]))
        self.assertTrue(any("exactly equal" in error for error in result["errors"]))

    def test_generation_order_and_invalid_2026_title_are_blocked(self):
        report = self.report()
        report["title_options_generation"]["started_at"] = "2026-07-30T09:59:00+08:00"
        report["title_options_2026"][0]["title"] = "CareCooo Produkt, Weiß"
        result = self.validate_archived(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("started before" in error for error in result["errors"]))
        self.assertTrue(any("core_product_phrase" in error for error in result["errors"]))

    def test_reference_title_is_fully_decomposed_and_dual_value_phrases_are_auditable(self):
        report = self.report()
        result = self.validate_archived(report)
        self.assertTrue(result["ok"], result["errors"])
        analysis = report["title_options_generation"]["reference_phrase_analysis"]
        dual = {item["source_text"] for item in analysis if item["priority"] == "dual_value"}
        self.assertEqual(
            dual,
            {"selbstklebend", "aus dickem Sisal", "und rutschfest", "schützt Sofa und Möbel"},
        )
        self.assertEqual(len(report["title_options_2026"][0]["title"]), 66)
        for option in report["title_options_2026"]:
            self.assertLessEqual(len(option["title"]), 75)
            self.assertLessEqual(len(option["item_highlights"]), 125)
            self.assertNotIn("|", option["title"])
            self.assertNotIn("|", option["item_highlights"])

    def test_incomplete_decomposition_and_unsupported_addition_are_blocked(self):
        report = self.report()
        report["title_options_generation"]["reference_phrase_analysis"].pop()
        report["title_options_2026"][0]["additional_verified_phrases"][0]["fact_refs"] = []
        result = self.validate_archived(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("completely decompose" in error for error in result["errors"]))
        self.assertTrue(any("direct product evidence" in error for error in result["errors"]))

    def test_phrase_order_and_unrelated_controlled_rewrite_are_blocked(self):
        report = self.report()
        analysis = report["title_options_generation"]["reference_phrase_analysis"]
        analysis[2]["source_text"], analysis[3]["source_text"] = (
            analysis[3]["source_text"],
            analysis[2]["source_text"],
        )
        analysis[2]["normalized_text"] = analysis[2]["source_text"].casefold()
        analysis[3]["normalized_text"] = analysis[3]["source_text"].casefold()
        result = self.validate_archived(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("exact reference-title text in source order" in error for error in result["errors"]))

        report = self.report()
        option = report["title_options_2026"][0]
        option["title"] = option["title"].replace("Sisal", "stabil")
        option["reference_phrase_allocation"][3]["realization"] = "stabil"
        result = self.validate_archived(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("controlled_rewrite introduces content" in error for error in result["errors"]))

    def test_high_priority_omission_requires_a_chinese_reason(self):
        report = self.report()
        allocation = report["title_options_2026"][1]["reference_phrase_allocation"][2]
        allocation.update({
            "placement": "omitted",
            "realization": "",
            "reuse_type": "omitted",
            "reason_code": "character_limit",
            "reason": "",
        })
        report["title_options_2026"][1]["title"] = report["title_options_2026"][1]["title"].replace(
            "selbstklebend ", ""
        )
        result = self.validate_archived(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("non-empty Chinese explanation" in error for error in result["errors"]))

    def test_new_reports_without_v4_method_are_blocked(self):
        for method in ("", "legacy_reference_phrase_allocation_v1", "legacy_reference_phrase_allocation_v2", "legacy_reference_phrase_allocation_v3"):
            with self.subTest(method=method or "empty"):
                report = self.report()
                if method:
                    report["title_options_generation"]["method"] = method
                else:
                    report["title_options_generation"].pop("method")
                result = VALIDATOR.validate_report(report)
                self.assertFalse(result["ok"])
                self.assertTrue(any("must use" in error for error in result["errors"]))

    def test_legacy_reports_without_new_method_are_read_only_compatible(self):
        report = self.report()
        report["title_options_generation"].pop("method")
        report["title_options_generation"].pop("reference_phrase_analysis")
        for option in report["title_options_2026"]:
            option.pop("reference_phrase_allocation")
            option.pop("additional_verified_phrases")
        result = VALIDATOR.validate_report(report, allow_legacy_title_method=True)
        self.assertTrue(result["ok"], result["errors"])

    def test_validator_cli_accepts_complete_handoff(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as temp:
            report_path = Path(temp) / "listing-report.json"
            artifact_path = Path(temp) / "legacy-listing-result-B0GKDK191Q.json"
            request_path = Path(temp) / "legacy-listing-request-B0GKDK191Q.json"
            raw_output_path = Path(temp) / "legacy-listing-raw-output-B0GKDK191Q.md"
            validation_path = Path(temp) / "validation.json"
            report["legacy_generation"]["artifact_path"] = str(artifact_path)
            request_path.write_text(json.dumps({
                "source_skill": "amazon-listing-optimization",
                "source_skill_path": VALIDATOR.SOURCE_SKILL_PATH,
                "mode": report["mode"],
                "asin": report["asin"],
                "marketplace": report["marketplace"],
                "language": "de_DE",
                "tone": "Professional",
                "core_keywords": ["kratzmatte selbstklebend"],
                "listing_eligible_keywords": [
                    {"keyword": "kratzmatte selbstklebend", "metrics": {"search_volume": 1000}}
                ],
                "created_at": "2026-07-30T09:59:00+08:00",
                "invocation_id": report["legacy_generation"]["invocation_id"],
                "input_manifest": report["legacy_generation"]["input_manifest"],
            }, ensure_ascii=False), encoding="utf-8")
            listing = report["legacy_generation"]["legacy_listing"]
            raw_output = "\n\n".join([
                "# Optimized Listing — Ready to Use",
                "## Title\n" + listing["title"],
                "## Bullet Points\n" + "\n".join(listing["bullets"]),
                "## Description\n" + listing["description"],
                "## Backend Search Terms\n" + listing["backend_search_terms"],
                "# Audit Report",
                "## Keyword Coverage\nValidated keyword coverage.",
            ])
            raw_output_path.write_text(raw_output, encoding="utf-8")
            report["legacy_generation"].update({
                "request_path": str(request_path),
                "request_sha256": VALIDATOR.file_sha256(request_path),
                "raw_output_path": str(raw_output_path),
                "raw_output_sha256": VALIDATOR.file_sha256(raw_output_path),
            })
            artifact = self.artifact(report)
            artifact["artifact_path"] = str(artifact_path)
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            artifact_path.write_text(json.dumps(artifact, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate-legacy-handoff.py"),
                    "--input",
                    str(report_path),
                    "--legacy-artifact",
                    str(artifact_path),
                    "--allow-legacy-title-method",
                    "--output",
                    str(validation_path),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertTrue(json.loads(validation_path.read_text(encoding="utf-8"))["ok"])

            raw_output_path.write_text("# Output\nmissing fields\n", encoding="utf-8")
            failed = self.validate_archived(report, artifact)
            self.assertFalse(failed["ok"])
            self.assertTrue(any("raw_output_sha256" in error for error in failed["errors"]))

            raw_output_path.write_text(
                raw_output.replace("# Audit Report", "").replace(
                    "## Keyword Coverage\nValidated keyword coverage.", ""
                ),
                encoding="utf-8",
            )
            new_hash = VALIDATOR.file_sha256(raw_output_path)
            report["legacy_generation"]["raw_output_sha256"] = new_hash
            artifact["raw_output_sha256"] = new_hash
            missing_audit = self.validate_archived(report, artifact)
            self.assertFalse(missing_audit["ok"])
            self.assertTrue(any("audit sections" in error for error in missing_audit["errors"]))

    def test_raw_output_must_contain_exact_legacy_listing_fields(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as temp:
            request_path = Path(temp) / "legacy-listing-request-B0GKDK191Q.json"
            raw_output_path = Path(temp) / "legacy-listing-raw-output-B0GKDK191Q.md"
            request_path.write_text(json.dumps({
                "source_skill": VALIDATOR.SOURCE_SKILL,
                "source_skill_path": VALIDATOR.SOURCE_SKILL_PATH,
                "mode": "B",
                "asin": report["asin"],
                "marketplace": report["marketplace"],
                "language": "de_DE",
                "tone": "Professional",
                "core_keywords": ["kratzmatte selbstklebend"],
                "listing_eligible_keywords": [
                    {"keyword": "kratzmatte selbstklebend", "metrics": {"search_volume": 1000}}
                ],
                "invocation_id": report["legacy_generation"]["invocation_id"],
                "created_at": report["legacy_generation"]["started_at"],
                "input_manifest": report["legacy_generation"]["input_manifest"],
            }, ensure_ascii=False), encoding="utf-8")
            raw_output_path.write_text(report["listing"]["title"], encoding="utf-8")
            report["legacy_generation"].update({
                "request_path": str(request_path),
                "request_sha256": VALIDATOR.file_sha256(request_path),
                "raw_output_path": str(raw_output_path),
                "raw_output_sha256": VALIDATOR.file_sha256(raw_output_path),
            })
            artifact = self.artifact(report)
            result = self.validate_archived(report, artifact)
            self.assertFalse(result["ok"])
            self.assertTrue(any("exact structured Listing fields" in error for error in result["errors"]))

    def test_skill_documents_mandatory_dependency_before_2026_generation(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        dependency = "/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md"
        self.assertIn(dependency, skill)
        self.assertIn("legacy-listing-request-<ASIN>.json", skill)
        self.assertIn("legacy-listing-raw-output-<ASIN>.md", skill)
        self.assertIn("legacy-listing-result-<ASIN>.json", skill)
        self.assertLess(skill.index("## 阶段 2：传统 Listing 优化"), skill.index("## 阶段 3：2026 短标题与商品亮点"))
        self.assertIn("validate-legacy-handoff.py", skill)
        self.assertIn("execution_provenance", skill)
        self.assertIn("adapter_invocation_id", skill)
        self.assertIn("不得由编排层、脚本或模型自行编造", skill)
        self.assertIn("传统标题不是短标题草稿", skill)
        self.assertIn("执行且只能执行 `legacy_reference_phrase_allocation_v4`", skill)
        self.assertIn("--allow-legacy-title-method", skill)

    def test_mode_b_blocker_uses_equivalent_public_recovery_before_blocking(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        retrieval = (ROOT / "references" / "web-retrieval-workflow.md").read_text(encoding="utf-8")
        self.assertIn("重新执行一次 Mode B", skill)
        self.assertIn("chrome:control-chrome", skill)
        self.assertIn("两条路径均不可用才阻塞", skill)
        self.assertIn("Chrome", retrieval)
        self.assertIn("不得读取 XLSM", skill)

    def test_only_confirmation_is_proactive_gate_and_passive_blockers_are_actionable(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("确认执行` 是唯一主动、强制等待用户确认", skill)
        self.assertIn("不得新增审批门禁、人工复核门禁、用户选择门禁、确认提示或“等待用户回复”步骤", skill)
        self.assertIn("不得主动设置任何阻塞、确认、审批或等待用户回复的环节", skill)
        self.assertIn("blocker-report.md", skill)
        for label in ("阶段：", "原因：", "已尝试：", "解决方法：", "下次预防：", "继续条件："):
            self.assertIn(label, skill)


if __name__ == "__main__":
    unittest.main()
