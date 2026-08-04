from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook, load_workbook


SCRIPT = Path(__file__).parents[1] / "scripts" / "workflow.py"
SPEC = importlib.util.spec_from_file_location("listing_workflow", SCRIPT)
WORKFLOW = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WORKFLOW)


class Args:
    pass


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self._retrieval_evidence_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._retrieval_evidence_temp.cleanup)
        self._retrieval_evidence_counter = 0

    def test_confirmation_review_filename_includes_identity_and_date(self):
        value = {
            "primary_asin": "B0GKDK191Q",
            "core_keywords": ["kratzmatte selbstklebend"],
            "core_keyword_chinese_name": "自粘式猫抓垫",
            "marketplace": "DE",
        }
        generated = WORKFLOW.confirmation_review_filename(
            value, WORKFLOW.dt.datetime(2026, 8, 4, tzinfo=WORKFLOW.dt.timezone.utc)
        )
        self.assertEqual(
            generated,
            "自粘式猫抓垫-confirmation-review-B0GKDK191Q-kratzmatte-selbstklebend-DE-20260804.md",
        )

    def test_confirmation_review_filename_preserves_chinese_core_keyword(self):
        value = {
            "primary_asin": "B0GKDK191Q",
            "core_keywords": ["猫抓垫"],
            "core_keyword_chinese_name": "猫抓垫",
            "marketplace": "DE",
        }
        generated = WORKFLOW.confirmation_review_filename(
            value, WORKFLOW.dt.datetime(2026, 8, 4, tzinfo=WORKFLOW.dt.timezone.utc)
        )
        self.assertEqual(
            generated,
            "猫抓垫-confirmation-review-B0GKDK191Q-keyword-DE-20260804.md",
        )

    def test_confirmation_review_filename_removes_unsafe_chinese_prefix_characters(self):
        value = {
            "primary_asin": "B0GKDK191Q",
            "core_keywords": ["kratzmatte selbstklebend"],
            "core_keyword_chinese_name": "自粘式/猫抓垫:*?\x00",
            "marketplace": "DE",
        }
        generated = WORKFLOW.confirmation_review_filename(
            value, WORKFLOW.dt.datetime(2026, 8, 4, tzinfo=WORKFLOW.dt.timezone.utc)
        )
        self.assertTrue(generated.startswith("自粘式猫抓垫-confirmation-review-"))
        self.assertNotRegex(generated, r'[\\/:*?"<>|\x00-\x1f\x7f]')

    def test_normalize_job_requires_chinese_core_keyword_translation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = self.base_input(root)
            value.pop("core_keyword_chinese_name")
            with self.assertRaisesRegex(ValueError, "core_keyword_chinese_name"):
                WORKFLOW.normalize_job(value, root / "run")
            value["core_keyword_chinese_name"] = "self adhesive cat mat"
            with self.assertRaisesRegex(ValueError, "必须包含中文字符"):
                WORKFLOW.normalize_job(value, root / "run")

    def test_normalize_job_reuses_chinese_core_keyword(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = self.base_input(root)
            value["core_keywords"] = ["猫抓垫"]
            value.pop("core_keyword_chinese_name")
            normalized = WORKFLOW.normalize_job(value, root / "run")
            self.assertEqual(normalized["core_keyword_chinese_name"], "猫抓垫")

    def test_inspect_and_resume_do_not_promote_missing_stages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "job.json").write_text(json.dumps({"primary_asin": "B0F4NDR1ZB"}), encoding="utf-8")
            (root / "status.json").write_text(json.dumps({"phase": "keywords_ready", "artifacts": {}}), encoding="utf-8")
            args = Args()
            args.run_dir = str(root)
            inspection = WORKFLOW.inspect_run(args)
            self.assertEqual(inspection["recorded_phase"], "keywords_ready")
            self.assertEqual(inspection["next_phase"], "keywords_ready")
            resumed = WORKFLOW.resume_plan(args)
            self.assertTrue(resumed["resumed"])
            self.assertEqual(resumed["phase"], "prepared")

    def workbook(self, root: Path) -> Path:
        path = root / "爱尔兰-分类商品报告.xlsm"
        workbook = Workbook()
        workbook.save(path)
        return path

    def base_input(self, root: Path) -> dict:
        keywords = root / "keywords.csv"
        keywords.write_text("keyword,volume\ncat window bed,1000\n", encoding="utf-8")
        return {
            "schema_version": 1,
            "primary_asin": "B0F4NDR1ZB",
            "marketplace": "爱尔兰",
            "core_keywords": "cat window bed、cat hammock window",
            "core_keyword_chinese_name": "猫窗床",
            "competitor_asins": ["B0F4P6NKCB", "B0F5WB2Z5B"],
            "selling_points": "柔软仿兔毛绒、强力吸盘",
            "variants": ["B0F596K897-灰色-M(适合中型猫咪)", "B0GT99T4SQ-绿色-L"],
            "keyword_source": {"mode": "uploaded", "files": [str(keywords)]},
            "category_workbook": str(self.workbook(root)),
            "workspace": str(root),
        }

    def ppc_ready_input(self, root: Path) -> dict:
        value = self.base_input(root)
        value["ppc_campaign"] = {
            "monthly_ad_budget": "EUR 900",
            "selling_price": 39.99,
            "landed_cost": 12.5,
            "amazon_fees": 8.4,
            "conversion_rate": "未知",
            "product_stage": "新品",
        }
        return value

    def original_listing_binding(
        self, title: str, source: str = "browser", asin: str = "B0F4NDR1ZB",
        marketplace: str = "IE",
    ) -> dict:
        # 原 Listing 不再由编排技能采集；仅保留下游审核字段所需的最小夹具。
        return {"before_after": [{"section": "标题", "before": title, "after": "Optimized title"}]}

        retrieved_at = "2026-07-31T02:25:06+00:00"
        bullets = [f"Original bullet {index}" for index in range(1, 6)]
        description = "Original description"

        def attempt(
            source_name: str, status: str, verified_fields: list[str],
            field_values: dict | None = None, missing_fields: list[str] | None = None,
        ) -> dict:
            record = {
                "source": source_name,
                "target_role": "optimized_asin",
                "asin": asin,
                "marketplace": marketplace,
                "executor": f"test:{source_name}",
                "url": f"/tmp/{asin}.xlsm" if source_name == "xlsm" else f"https://example.test/{asin}/{source_name}",
                "retrieved_at": retrieved_at,
                "status": status,
                "verified_fields": verified_fields,
                "missing_fields": missing_fields or [],
                "field_values": field_values or {},
                "failure_reason": "测试来源未取得剩余字段" if status == "failed" else "",
            }
            self._retrieval_evidence_counter += 1
            evidence_path = Path(self._retrieval_evidence_temp.name) / (
                f"{self._retrieval_evidence_counter:03d}-{asin}-{source_name}.json"
            )
            evidence_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return {
                **record,
                "evidence_path": str(evidence_path),
                "evidence_sha256": WORKFLOW.sha256(evidence_path),
            }

        if source == "xlsm":
            title_field = "  XLSM title  "
            highlight_field = "  XLSM highlight  "
            reference_title = "XLSM title XLSM highlight"
            attempts = [
                *(attempt(name, "failed", [], missing_fields=["title", "bullets", "description"])
                  for name in WORKFLOW.WEB_LISTING_SOURCE_CHAIN),
                attempt("xlsm", "complete", ["title", "bullets", "description"], {
                    "title": reference_title, "bullets": bullets, "description": description,
                }),
            ]
            return {
                "marketplace": marketplace,
                "original_listing": {"title": reference_title, "bullets": bullets, "description": description},
                "source_retrieval": {
                    "target_role": "optimized_asin", "asin": asin, "marketplace": marketplace,
                    "required_fields": ["title", "bullets", "description"],
                    "attempts": attempts,
                    "resolved_fields": {
                        "title": {"value": reference_title, "source": "xlsm", "attempt_index": 7},
                        "bullets": {"value": bullets, "source": "xlsm", "attempt_index": 7},
                        "description": {"value": description, "source": "xlsm", "attempt_index": 7},
                    },
                    "xlsm_fallback": {
                        "title_field": title_field,
                        "item_highlight_field": highlight_field,
                        "reference_title": reference_title,
                    },
                    "missing_fields": [],
                },
                "before_after": [{"section": "标题", "before": reference_title, "after": "Optimized title"}],
            }
        attempts = [
            attempt("browser", "partial", ["title"], {"title": title}, ["bullets", "description"]),
            *(attempt(name, "failed", [], missing_fields=["bullets", "description"])
              for name in WORKFLOW.WEB_LISTING_SOURCE_CHAIN[1:]),
            attempt("xlsm", "complete", ["bullets", "description"], {
                "bullets": bullets, "description": description,
            }),
        ]
        return {
            "marketplace": marketplace,
            "original_listing": {"title": title, "bullets": bullets, "description": description},
            "source_retrieval": {
                "target_role": "optimized_asin", "asin": asin, "marketplace": marketplace,
                "required_fields": ["title", "bullets", "description"],
                "attempts": attempts,
                "resolved_fields": {
                    "title": {"value": title, "source": "browser", "attempt_index": 1},
                    "bullets": {"value": bullets, "source": "xlsm", "attempt_index": 7},
                    "description": {"value": description, "source": "xlsm", "attempt_index": 7},
                },
                "missing_fields": [],
            },
            "before_after": [{"section": "标题", "before": title, "after": "Optimized title"}],
        }

    def write_keyword_validation(self, root: Path, job: dict) -> tuple[Path, Path, str]:
        root.mkdir(parents=True, exist_ok=True)
        pool_path = root / "keyword-pool.json"
        pool_path.write_text(json.dumps({
            "keywords": [
                {"id": "KW-001", "keyword": "cat window bed", "listing_eligible": True, "ppc_eligible": True},
                {"id": "KW-002", "keyword": "cat hammock window", "listing_eligible": True, "ppc_eligible": True},
                {"id": "KW-003", "keyword": "cat window perch", "listing_eligible": True, "ppc_eligible": True},
                {"id": "KW-004", "keyword": "window hammock for cats", "listing_eligible": True, "ppc_eligible": True},
                {"id": "KW-005", "keyword": "verified product detail", "qa_eligible": True},
            ],
        }, ensure_ascii=False), encoding="utf-8")
        pool_sha = WORKFLOW.sha256(pool_path)
        validation_path = root / "keyword-validation.json"
        validation_path.write_text(json.dumps({
            "ok": True,
            "errors": [],
            "marketplace": job["marketplace"],
            "language": job["marketplace_language"],
            "pool": str(pool_path),
            "pool_sha256": pool_sha,
        }, ensure_ascii=False), encoding="utf-8")
        return validation_path, pool_path, pool_sha

    def write_valid_keyword_pool(
        self, root: Path, job: dict, source_count: int, autocomplete_count: int | None = None,
    ) -> tuple[Path, Path, dict]:
        root.mkdir(parents=True, exist_ok=True)
        core_keywords = list(job["core_keywords"])
        entries = []
        source_terms_remaining = source_count
        for keyword in core_keywords:
            sources = ["user_core"]
            if source_terms_remaining:
                sources.append("uploaded_file")
                source_terms_remaining -= 1
            entries.append({
                "keyword": keyword,
                "sources": sources,
                "metrics": {"search_volume": 1000} if "uploaded_file" in sources else {},
                "relevance": "high",
                "selling_point_matches": [],
                "listing_eligible": True,
                "ppc_eligible": True,
                "qa_eligible": True,
            })
        for index in range(source_terms_remaining):
            entries.append({
                "keyword": f"uploaded cat keyword {index + 1}",
                "sources": ["uploaded_file"],
                "metrics": {"search_volume": 100 - index},
                "relevance": "high",
                "selling_point_matches": [],
                "listing_eligible": True,
                "ppc_eligible": True,
                "qa_eligible": True,
            })

        fallback_triggered = source_count < 10
        if autocomplete_count is None:
            autocomplete_count = max(0, 10 - source_count) if fallback_triggered else 0
        for index in range(autocomplete_count):
            entries.append({
                "keyword": f"soft suction cat window term {index + 1}",
                "sources": ["amazon_autocomplete"],
                "metrics": {},
                "relevance": "high",
                "selling_point_matches": ["柔软仿兔毛绒", "强力吸盘"],
                "listing_eligible": True,
                "ppc_eligible": True,
                "qa_eligible": True,
            })
        for index, entry in enumerate(entries, start=1):
            entry["id"] = f"KW-{index:03d}"
            entry["normalized_keyword"] = WORKFLOW.normalize_keyword(entry["keyword"])

        seeds = []
        if fallback_triggered:
            for index, keyword in enumerate(core_keywords, start=1):
                evidence_path = root / f"amazon-autocomplete-{index}.json"
                evidence_path.write_text(json.dumps({
                    "schema_version": 1,
                    "keyword": keyword,
                    "marketplace": job["marketplace"],
                    "suggestions": [f"{keyword} suggestion"],
                }, ensure_ascii=False), encoding="utf-8")
                seeds.append({
                    "original": keyword,
                    "localized": keyword,
                    "marketplace": job["marketplace"],
                    "status": "complete",
                    "source_artifact": str(evidence_path),
                    "source_sha256": WORKFLOW.sha256(evidence_path),
                })
        if not fallback_triggered:
            fallback_status = "not_needed"
        elif source_count + autocomplete_count >= 10:
            fallback_status = "complete"
        else:
            fallback_status = "insufficient"
        pool = {
            "schema_version": 1,
            "marketplace": job["marketplace"],
            "language": job["marketplace_language"],
            "minimum_usable_keywords": 10,
            "pre_fallback_usable_count": source_count,
            "post_fallback_usable_count": source_count + autocomplete_count,
            "fallback": {
                "triggered": fallback_triggered,
                "status": fallback_status,
                "skill": "amazon-keyword-research" if fallback_triggered else "",
                "seeds": seeds,
            },
            "keywords": entries,
            "excluded": [{
                "keyword": "free unrelated product",
                "sources": ["amazon_autocomplete"],
                "reason": "与商品类别和购买意图不相关",
            }],
            "warnings": [] if source_count + autocomplete_count >= 10 else [
                f"关键词数据不足提醒：自动补词后仅有 {source_count + autocomplete_count} 个有效采集词。"
            ],
        }
        pool_path = root / "keyword-pool-valid.json"
        pool_path.write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
        args = Args()
        args.job = str(root / "job.json")
        args.pool = str(pool_path)
        args.output = str(root / "keyword-validation-valid.json")
        result = WORKFLOW.validate_keyword_pool(args)
        return pool_path, Path(args.output), result

    def ppc_plan(self, job: dict, keyword_pool_sha: str = "") -> dict:
        profit = 39.99 - 12.5 - 8.4
        return {
            "schema_version": 1,
            "mode": "build",
            "primary_asin": job["primary_asin"],
            "marketplace": job["marketplace"],
            "keyword_pool_sha256": keyword_pool_sha,
            "currency": "EUR",
            "financial_framework": {
                "selling_price": 39.99,
                "monthly_ad_budget": 900,
                "profit_before_ads": profit,
                "break_even_acos": profit / 39.99,
                "target_acos_launch": 0.43,
                "target_acos_mature": 0.3,
                "conversion_rate": None,
                "max_cpc": None,
                "data_sources": ["用户成本数据", "Amazon IE 主 ASIN 页面"],
                "assumptions": [],
            },
            "data_quality": {
                "financial_confidence": "fact_supported",
                "input_data_quality": "用户提供成本、售价和预算，关键词仅保留符合资格的真实来源词。",
                "financial_limitations": "未提供转化率，因此不输出金额 CPC 或单词出价。",
                "keyword_boundary": "不使用历史广告数据，竞品仅以用户提供 ASIN 交由 PPC 技能自行评估。",
            },
            "bid_guidance": {
                "mode": "formula_and_coefficients",
                "formula": "Max CPC = 售价 × 目标 ACoS × 已验证转化率；未提供转化率时仅作为待核验公式。",
                "coefficients": {"exact": 1.0, "broad": 0.75, "auto": 0.6, "product_targeting": 0.6},
                "seller_central_check": "在 Seller Central 核验建议竞价后，以财务上限和系数决定实际金额。",
            },
            "generation_provenance": {"fixture": True},
            "keyword_sources": ["用户核心关键词", "统一关键词结果", "竞品 Listing"],
            "campaigns": [
                {"type": "auto", "name": "Cat Window Bed - Auto"},
                {"type": "manual_exact", "name": "Cat Window Bed - Exact"},
                {"type": "manual_broad", "name": "Cat Window Bed - Broad"},
                {"type": "product_targeting", "name": "Cat Window Bed - ASIN Targeting"},
            ],
            "copy_blocks": {
                "manual_exact_keywords": ["cat window bed", "cat hammock window"],
                "manual_broad_keywords": ["cat window perch", "window hammock for cats"],
                "auto_negative_exact_keywords": ["cat window bed", "cat hammock window"],
                "broad_negative_exact_keywords": ["cat window bed", "cat hammock window"],
                "negative_phrase_keywords": ["free", "diy"],
                "product_targeting_asins": ["B0F4P6NKCB", "B0F5WB2Z5B"],
            },
            "budget_summary": [{"campaign": "Auto", "daily_budget": 9}],
            "launch_schedule": ["第1天：启动 Auto 和 Exact 广告活动"],
            "optimization_plan_4_weeks": ["第1周：收集搜索词"],
            "risk_notes": ["有建议竞价时使用 Amazon Suggested Bid"],
        }

    def ppc_markdown(self, plan: dict) -> str:
        labels = {
            "manual_exact_keywords": "Manual Exact Keywords",
            "manual_broad_keywords": "Manual Broad Keywords",
            "auto_negative_exact_keywords": "Auto Negative Exact Keywords",
            "broad_negative_exact_keywords": "Broad Negative Exact Keywords",
            "negative_phrase_keywords": "Negative Phrase Keywords",
            "product_targeting_asins": "Product Targeting ASINs",
        }
        sections = [
            "# PPC 广告方案",
            "## 输入数据质量\n用户事实、统一关键词池和竞品 ASIN 已按来源绑定。",
            "## 财务依据与默认值影响\n财务参数按输入来源使用，默认值不代表利润预测。",
            "## 关键词来源与排除边界\n仅使用 ppc_eligible 关键词，不使用历史广告数据。",
            "## 竞价依据限制\n未提供转化率时仅提供公式和系数，不提供金额 CPC。",
            "## Campaign 设计理由\n由 amazon-ppc-campaign Mode A 根据事实输入生成。",
        ]
        for key, label in labels.items():
            sections.extend([f"## {label}", "```text", "\n".join(plan["copy_blocks"][key]), "```"])
        return "\n\n".join(sections) + "\n"

    def write_valid_ppc_artifacts(self, root: Path, job: dict) -> tuple[Path, Path, Path]:
        keyword_validation, _keyword_pool, keyword_pool_sha = self.write_keyword_validation(root, job)
        plan = self.ppc_plan(job, keyword_pool_sha)
        plan_path = root / f"ppc-campaign-plan-{job['primary_asin']}.json"
        markdown_path = root / f"ppc-campaign-plan-{job['primary_asin']}.md"
        validation_path = root / "ppc-validation.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        markdown_path.write_text(self.ppc_markdown(plan), encoding="utf-8")
        args = Args()
        args.job = str(root / "job.json")
        args.keyword_validation = str(keyword_validation)
        args.plan = str(plan_path)
        args.markdown = str(markdown_path)
        args.output = str(validation_path)
        WORKFLOW.validate_ppc_plan(args)
        return plan_path, markdown_path, validation_path

    def write_report_validation(
        self, root: Path, job: dict, reports: list[str], keyword_pool_sha: str,
    ) -> Path:
        path = root / "report-validation.json"
        checked = []
        for report_value in reports:
            report_path = Path(report_value).resolve()
            report = WORKFLOW.load_json(report_path)
            artifact_path = root / f"legacy-listing-result-{report['asin']}.json"
            request_path = root / f"legacy-listing-request-{report['asin']}.json"
            raw_output_path = root / f"legacy-listing-raw-output-{report['asin']}.md"
            source_skill_path = Path("/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md")
            source_skill_sha = WORKFLOW.sha256(source_skill_path)
            legacy_listing = report.get("listing") or {
                "title": "", "bullets": [], "description": "", "backend_search_terms": "",
            }
            input_manifest = (report.get("legacy_generation") or {}).get("input_manifest") or {}
            invocation_id = f"INV-{report['asin']}-TEST-RUN"
            started_at = "2026-07-31T02:24:00+00:00"
            request_path.write_text(json.dumps({
                "source_skill": "amazon-listing-optimization",
                "source_skill_path": str(source_skill_path),
                "mode": report.get("mode", "B"),
                "asin": report["asin"],
                "invocation_id": invocation_id,
                "created_at": started_at,
                "input_manifest": input_manifest,
            }, ensure_ascii=False), encoding="utf-8")
            raw_output_path.write_text("\n\n".join([
                "# Optimized Listing — Ready to Use",
                "## Title\n" + str(legacy_listing.get("title", "")),
                "## Bullet Points\n" + "\n".join(
                    str(item) for item in legacy_listing.get("bullets", [])
                ),
                "## Description\n" + str(legacy_listing.get("description", "")),
                "## Backend Search Terms\n" + str(legacy_listing.get("backend_search_terms", "")),
                "# Audit Report",
                "## Keyword Coverage\nTest coverage.",
            ]), encoding="utf-8")
            legacy = report.setdefault("legacy_generation", {})
            legacy.update({
                "source_skill": "amazon-listing-optimization",
                "source_skill_path": str(source_skill_path),
                "source_skill_sha256": source_skill_sha,
                "artifact_path": str(artifact_path.resolve()),
                "invocation_id": invocation_id,
                "started_at": started_at,
                "request_path": str(request_path.resolve()),
                "request_sha256": WORKFLOW.sha256(request_path),
                "raw_output_path": str(raw_output_path.resolve()),
                "raw_output_sha256": WORKFLOW.sha256(raw_output_path),
                "mode": report.get("mode", "B"),
                "input_manifest": input_manifest,
                "legacy_listing": legacy_listing,
            })
            artifact_path.write_text(json.dumps(legacy, ensure_ascii=False), encoding="utf-8")
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            checked.append({
                "asin": report["asin"],
                "report": str(report_path),
                "report_sha256": WORKFLOW.sha256(report_path),
                "legacy_artifact": str(artifact_path.resolve()),
                "legacy_artifact_sha256": WORKFLOW.sha256(artifact_path),
                "legacy_request": str(request_path.resolve()),
                "legacy_request_sha256": WORKFLOW.sha256(request_path),
                "legacy_raw_output": str(raw_output_path.resolve()),
                "legacy_raw_output_sha256": WORKFLOW.sha256(raw_output_path),
                "source_skill_sha256": source_skill_sha,
            })
        path.write_text(json.dumps({
            "ok": True,
            "marketplace": job["marketplace"],
            "keyword_pool_sha256": keyword_pool_sha,
            "expected_asins": sorted(job["target_asins"]),
            "checked": checked,
            "errors": [],
        }, ensure_ascii=False), encoding="utf-8")
        return path

    def write_manual_review_packet(
        self, root: Path, job_path: Path, plan_path: Path, job: dict,
        ppc_plan: Path, ppc_markdown: Path, ppc_validation: Path,
    ) -> tuple[Path, Path, dict[str, Path]]:
        root = root.resolve()
        files = {
            "listing_optimization": root / f"listing-optimization-plan-{job['primary_asin']}.md",
            "short_title_highlights": root / f"short-title-highlights-plan-{job['primary_asin']}.md",
            "ppc_campaign": ppc_markdown.resolve(),
            "xlsm_replacement": root / "xlsm-replacement-plan.md",
            "rufus_qa": root / f"rufus-qa-plan-{job['primary_asin']}.md",
        }
        files["listing_optimization"].write_text("# Listing 优化方案\n\n完整 Listing 正文\n", encoding="utf-8")
        files["short_title_highlights"].write_text("# 2026 短标题与商品亮点方案\n\n三组完整方案\n", encoding="utf-8")
        files["xlsm_replacement"].write_text("# XLSM 文件替换方案\n\n完整替换字段\n", encoding="utf-8")
        labels = {
            "listing_optimization": "Listing 优化方案文本文件",
            "short_title_highlights": "2026 短标题与商品亮点方案文本文件",
            "ppc_campaign": "PPC 广告方案文本文件",
            "xlsm_replacement": "XLSM 文件替换方案文本文件",
            "rufus_qa": "Rufus Q/A 方案文本文件",
        }
        listings = []
        keyword_pool_sha = WORKFLOW.load_json(ppc_validation)["keyword_pool_sha256"]
        for asin in job["target_asins"]:
            report_path = root / f"listing-optimization-report-{asin}.json"
            report = {"asin": asin, "marketplace": job["marketplace"], "keyword_pool_sha256": keyword_pool_sha}
            if asin == job["primary_asin"]:
                report["rufus_qa"] = self.rufus_qa(keyword_pool_sha=keyword_pool_sha)
            report_path.write_text(
                json.dumps(report, ensure_ascii=False),
                encoding="utf-8",
            )
            listings.append({"asin": asin, "report": str(report_path)})
        report_validation = self.write_report_validation(
            root, job, [item["report"] for item in listings], keyword_pool_sha,
        )
        rufus_validation = root / "rufus-qa-validation.json"
        rufus_args = Args()
        rufus_args.job = str(job_path)
        rufus_args.keyword_validation = WORKFLOW.load_json(ppc_validation)["keyword_validation"]
        rufus_args.ppc_validation = str(ppc_validation)
        rufus_args.report = listings[0]["report"]
        rufus_args.markdown = str(files["rufus_qa"])
        rufus_args.output = str(rufus_validation)
        WORKFLOW.validate_rufus_plan(rufus_args)
        deliverables = [
            {"kind": kind, "label": labels[kind], "path": str(path), "sha256": WORKFLOW.sha256(path)}
            for kind, path in files.items()
        ]
        packet = {
            "schema_version": 1,
            "status": "ready_for_user_review",
            "job": str(job_path),
            "plan": str(plan_path),
            "ppc_plan": str(ppc_plan),
            "ppc_validation": str(ppc_validation),
            "rufus_validation": str(rufus_validation),
            "report_validation": str(report_validation),
            "keyword_validation": WORKFLOW.load_json(ppc_validation)["keyword_validation"],
            "keyword_pool": str(Path(WORKFLOW.load_json(ppc_validation)["keyword_validation"]).with_name("keyword-pool.json")),
            "keyword_pool_sha256": WORKFLOW.load_json(ppc_validation)["keyword_pool_sha256"],
            "pre_confirmation_deliverables": deliverables,
            "listings": listings,
        }
        packet_path = root / "confirmation-review.json"
        packet_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
        markdown_path = root / "confirmation-review.md"
        markdown_path.write_text("\n\n".join(
            f"{path}\n\n{path.read_text(encoding='utf-8').rstrip()}" for path in files.values()
        ) + "\n", encoding="utf-8")
        return packet_path, markdown_path, files

    def rufus_qa(
        self, marketplace: str = "IE", language: str = "en_IE", keyword_pool_sha: str = "",
    ) -> dict:
        topics = (
            ["product_identity"] * 2
            + ["feature_material"] * 3
            + ["audience_use_case"] * 2
            + ["buyer_concern"] * 3
            + ["setup_care_included"] * 2
        )
        ids = [f"QA-{index:02d}" for index in range(1, 13)]
        return {
            "status": "complete",
            "target_count": 12,
            "marketplace": marketplace,
            "language": language,
            "items": [
                {
                    "id": qa_id,
                    "topic": topic,
                    "question": f"What verified product detail applies to shopper question {index}?",
                    "answer": f"Verified product detail {index} is documented in the seller materials.",
                    "question_zh": f"已验证的产品信息适用于买家问题 {index} 吗？",
                    "answer_zh": f"已验证的产品信息 {index} 已记录在卖家资料中。",
                    "semantic_keywords": [f"verified detail {index}"],
                    "evidence_refs": ["E-01"],
                    "keyword_refs": ["KW-005"],
                }
                for index, (qa_id, topic) in enumerate(zip(ids, topics), start=1)
            ],
            "evidence": [{
                "id": "E-01",
                "source_type": "user",
                "source_title": "用户商品资料",
                "source_url": "",
                "retrieved_at": "",
                "marketplace": marketplace,
                "verified_facts": ["用户资料支持测试用商品事实"],
                "used_by": ids,
            }],
            "limitations": [],
            "keyword_pool_sha256": keyword_pool_sha,
        }

    def test_prepare_parses_flexible_variants_and_ie(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = WORKFLOW.normalize_job(self.base_input(root), root / "run-1")
            self.assertEqual(value["marketplace"], "IE")
            self.assertEqual(value["marketplace_language"], "en_IE")
            self.assertEqual(value["target_asins"], ["B0F4NDR1ZB", "B0F596K897", "B0GT99T4SQ"])
            grey = value["variants"][1]
            self.assertEqual(grey["expected_title_terms"], ["Grey", "M"])
            self.assertEqual(grey["unresolved_segments"], ["适合中型猫咪"])
            self.assertTrue(value["model_review_required"])

    def test_competitor_limit_and_keyword_extensions_are_strict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = self.base_input(root)
            value["competitor_asins"] = ["B0F4P6NKCB", "B0F5WB2Z5B", "B0F5VTKYTK", "B0AAAAAAA1"]
            with self.assertRaisesRegex(ValueError, "最多 3"):
                WORKFLOW.normalize_job(value, root / "run")
            value = self.base_input(root)
            bad = root / "keywords.xls"
            bad.write_text("bad", encoding="utf-8")
            value["keyword_source"] = {"mode": "uploaded", "files": [str(bad)]}
            with self.assertRaisesRegex(ValueError, "不支持"):
                WORKFLOW.normalize_job(value, root / "run")

    def test_keyword_source_modes_support_uploaded_sellersprite_and_combined(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            uploaded = WORKFLOW.normalize_job(self.base_input(root), root / "uploaded")
            self.assertTrue(uploaded["keyword_source"]["use_uploaded_files"])
            self.assertFalse(uploaded["keyword_source"]["use_sellersprite"])

            sellersprite_input = self.base_input(root)
            sellersprite_input["keyword_source"] = {"mode": "sellersprite", "files": []}
            sellersprite = WORKFLOW.normalize_job(sellersprite_input, root / "sellersprite")
            self.assertFalse(sellersprite["keyword_source"]["use_uploaded_files"])
            self.assertTrue(sellersprite["keyword_source"]["use_sellersprite"])

            combined_input = self.base_input(root)
            combined_input["keyword_source"]["mode"] = "combined"
            combined = WORKFLOW.normalize_job(combined_input, root / "combined")
            self.assertTrue(combined["keyword_source"]["use_uploaded_files"])
            self.assertTrue(combined["keyword_source"]["use_sellersprite"])
            self.assertEqual(combined["keyword_source"]["relevance_min"], 30)
            self.assertEqual(combined["keyword_source"]["monthly_search_volume_min"], 1)

    def test_keyword_source_defaults_to_auto_without_files_or_sellersprite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = self.base_input(root)
            value.pop("keyword_source")
            job = WORKFLOW.normalize_job(value, root / "auto")
            self.assertEqual(job["keyword_source"]["mode"], "auto")
            self.assertFalse(job["keyword_source"]["use_uploaded_files"])
            self.assertFalse(job["keyword_source"]["use_sellersprite"])
            self.assertTrue(job["keyword_source"]["use_keyword_research_fallback"])
            self.assertEqual(job["keyword_source"]["minimum_usable_keywords"], 10)

    def test_keyword_pool_fallback_triggers_only_below_ten_collected_terms(self):
        for source_count, expected_trigger in ((0, True), (9, True), (10, False)):
            with self.subTest(source_count=source_count), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                job = WORKFLOW.normalize_job(self.base_input(root), root / "run")
                (root / "job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
                _pool, _validation, result = self.write_valid_keyword_pool(root, job, source_count)
                self.assertEqual(result["pre_fallback_usable_count"], source_count)
                self.assertIs(result["fallback_triggered"], expected_trigger)

    def test_keyword_pool_continues_with_warning_when_fallback_remains_sparse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.base_input(root), root / "run")
            (root / "job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            pool_path, _validation, result = self.write_valid_keyword_pool(
                root, job, source_count=0, autocomplete_count=0,
            )
            self.assertTrue(result["ok"])
            self.assertEqual(result["usable_keyword_count"], 2)
            self.assertEqual(result["post_fallback_usable_count"], 0)
            pool = WORKFLOW.load_json(pool_path)
            self.assertEqual(pool["fallback"]["status"], "insufficient")
            self.assertIn("关键词数据不足提醒", pool["warnings"][0])

    def test_keyword_pool_rejects_unicode_duplicates_and_wrong_selling_point_order(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.base_input(root), root / "run")
            (root / "job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            pool_path, _validation, _result = self.write_valid_keyword_pool(root, job, source_count=0)
            pool = WORKFLOW.load_json(pool_path)
            duplicate = dict(pool["keywords"][0])
            duplicate.update({
                "id": "KW-999",
                "keyword": "ＣＡＴ window bed",
                "normalized_keyword": "cat window bed",
                "sources": ["amazon_autocomplete"],
            })
            pool["keywords"].append(duplicate)
            pool_path.write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
            args = Args()
            args.job = str(root / "job.json")
            args.pool = str(pool_path)
            args.output = None
            with self.assertRaisesRegex(ValueError, "重复词"):
                WORKFLOW.validate_keyword_pool(args)

            pool["keywords"].pop()
            autocomplete = [item for item in pool["keywords"] if "amazon_autocomplete" in item["sources"]]
            autocomplete[0]["selling_point_matches"] = []
            autocomplete[-1]["selling_point_matches"] = ["强力吸盘"]
            pool_path.write_text(json.dumps(pool, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "匹配核心卖点"):
                WORKFLOW.validate_keyword_pool(args)

    def test_keyword_research_json_fixture_supports_all_thirteen_marketplaces(self):
        script = Path("/Users/apple/.agents/skills/amazon-keyword-research/scripts/research.sh")
        expected_domains = {
            "us": "amazon.com", "uk": "amazon.co.uk", "de": "amazon.de",
            "fr": "amazon.fr", "it": "amazon.it", "es": "amazon.es",
            "jp": "amazon.co.jp", "ca": "amazon.ca", "au": "amazon.com.au",
            "in": "amazon.in", "mx": "amazon.com.mx", "br": "amazon.com.br",
            "ie": "amazon.ie",
        }
        with tempfile.TemporaryDirectory() as temp:
            fixture = Path(temp) / "autocomplete.json"
            fixture.write_text(json.dumps({
                "suggestions": [
                    {"value": "Katzenbett weich"},
                    {"value": "猫用ベッド おすすめ"},
                    {"value": "lit pour chat d'été"},
                ]
            }, ensure_ascii=False), encoding="utf-8")
            environment = {**os.environ, "AMAZON_AUTOCOMPLETE_FIXTURE": str(fixture)}
            for marketplace, domain in expected_domains.items():
                with self.subTest(marketplace=marketplace):
                    completed = subprocess.run(
                        [str(script), "l'été 猫's bed", marketplace, "--format", "json"],
                        check=True, capture_output=True, text=True, env=environment,
                    )
                    payload = json.loads(completed.stdout)
                    self.assertEqual(payload["marketplace"], marketplace.upper())
                    self.assertEqual(payload["domain"], domain)
                    self.assertEqual(payload["successful_request_count"], 30)
                    self.assertEqual(len(payload["suggestions"]), 3)

    def test_keyword_source_mode_file_requirements_are_strict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)

            combined = self.base_input(root)
            combined["keyword_source"] = {"mode": "combined", "files": []}
            with self.assertRaisesRegex(ValueError, "至少需要一个"):
                WORKFLOW.normalize_job(combined, root / "combined")

            sellersprite = self.base_input(root)
            sellersprite["keyword_source"]["mode"] = "sellersprite"
            with self.assertRaisesRegex(ValueError, "不应同时指定"):
                WORKFLOW.normalize_job(sellersprite, root / "sellersprite")

            bad = root / "keywords.xls"
            bad.write_text("bad", encoding="utf-8")
            combined_bad = self.base_input(root)
            combined_bad["keyword_source"] = {"mode": "combined", "files": [str(bad)]}
            with self.assertRaisesRegex(ValueError, "不支持"):
                WORKFLOW.normalize_job(combined_bad, root / "combined-bad")

    def test_ppc_parameters_normalize_financial_inputs_and_missing_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ready = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "ready")
            ppc = ready["ppc_campaign"]
            self.assertEqual(ppc["currency"], "EUR")
            self.assertEqual(ppc["monthly_ad_budget"], 900)
            self.assertEqual(ppc["product_stage"], "launch")
            self.assertEqual(ppc["missing_user_inputs"], [])
            self.assertFalse(ppc["selling_price_requires_discovery"])

            defaulted = WORKFLOW.normalize_job(self.base_input(root), root / "missing")["ppc_campaign"]
            self.assertEqual(defaulted["monthly_ad_budget"], 600)
            self.assertEqual(defaulted["break_even_acos"], 0.4)
            self.assertEqual(defaulted["missing_user_inputs"], [])
            self.assertTrue(defaulted["defaults_applied"]["monthly_ad_budget"]["used"])
            self.assertTrue(defaulted["defaults_applied"]["break_even_acos"]["used"])
            self.assertEqual(defaulted["selling_price"], 40)
            self.assertTrue(defaulted["defaults_applied"]["selling_price"]["used"])
            self.assertEqual(defaulted["defaults_applied"]["selling_price"]["value"], 40)
            self.assertFalse(defaulted["selling_price_requires_discovery"])

            break_even_input = self.base_input(root)
            break_even_input["ppc_campaign"] = {
                "monthly_ad_budget": 600,
                "break_even_acos": "45%",
                "product_stage": "成熟期",
            }
            break_even = WORKFLOW.normalize_job(break_even_input, root / "break-even")["ppc_campaign"]
            self.assertEqual(break_even["break_even_acos"], 0.45)
            self.assertEqual(break_even["product_stage"], "mature")
            self.assertEqual(break_even["missing_user_inputs"], [])

    def test_default_budget_supports_us_eur_gbp_and_jpy(self):
        eur = WORKFLOW.normalize_ppc_campaign({}, "DE")
        usd = WORKFLOW.normalize_ppc_campaign({}, "US")
        self.assertEqual((eur["monthly_ad_budget"], eur["currency"]), (600, "EUR"))
        self.assertEqual((usd["monthly_ad_budget"], usd["currency"]), (600, "USD"))

        def exchange_rates(_url):
            return {"date": "2026-07-28", "rates": {"GBP": 0.75262, "JPY": 163.91}}

        with patch.object(WORKFLOW, "fetch_fx_json", side_effect=exchange_rates):
            gbp = WORKFLOW.normalize_ppc_campaign({}, "UK")
            jpy = WORKFLOW.normalize_ppc_campaign({}, "JP")
        self.assertEqual(gbp["monthly_ad_budget"], 451.57)
        self.assertEqual(jpy["monthly_ad_budget"], 98346)
        self.assertEqual(gbp["defaults_applied"]["monthly_ad_budget"]["rate_date"], "2026-07-28")
        self.assertEqual(jpy["defaults_applied"]["monthly_ad_budget"]["base_currency"], "USD")

    def test_default_budget_uses_fallback_and_blocks_when_all_sources_fail(self):
        calls = []

        def fallback(url):
            calls.append(url)
            if "frankfurter" in url:
                raise ValueError("primary unavailable")
            return {"time_last_update_unix": 1785196800, "rates": {"GBP": 0.75}}

        budget, metadata = WORKFLOW.resolve_default_monthly_budget("GBP", fallback)
        self.assertEqual(budget, 450)
        self.assertIn("open.er-api.com", metadata["source_url"])
        self.assertEqual(len(calls), 2)

        with self.assertRaisesRegex(ValueError, "汇率数据获取失败"):
            WORKFLOW.resolve_default_monthly_budget("GBP", lambda _url: (_ for _ in ()).throw(ValueError("offline")))

    def test_explicit_values_and_complete_costs_override_defaults(self):
        with patch.object(WORKFLOW, "fetch_fx_json") as fetcher:
            explicit = WORKFLOW.normalize_ppc_campaign({
                "monthly_ad_budget": 800,
                "currency": "GBP",
                "break_even_acos": "45%",
            }, "UK")
        fetcher.assert_not_called()
        self.assertEqual(explicit["monthly_ad_budget"], 800)
        self.assertEqual(explicit["break_even_acos"], 0.45)
        self.assertFalse(explicit["defaults_applied"]["monthly_ad_budget"]["used"])
        self.assertFalse(explicit["defaults_applied"]["break_even_acos"]["used"])

        complete_costs = WORKFLOW.normalize_ppc_campaign({
            "landed_cost": 10,
            "amazon_fees": 5,
        }, "DE")
        self.assertIsNone(complete_costs["break_even_acos"])
        self.assertEqual(complete_costs["landed_cost"], 10)
        self.assertFalse(complete_costs["defaults_applied"]["break_even_acos"]["used"])

        partial_costs = WORKFLOW.normalize_ppc_campaign({"landed_cost": 10}, "DE")
        self.assertEqual(partial_costs["break_even_acos"], 0.4)
        self.assertIsNone(partial_costs["landed_cost"])
        self.assertEqual(partial_costs["defaults_applied"]["ignored_incomplete_cost_inputs"], {"landed_cost": 10.0})

    def test_ppc_parameters_reject_wrong_marketplace_currency(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = self.ppc_ready_input(root)
            value["ppc_campaign"]["currency"] = "GBP"
            with self.assertRaisesRegex(ValueError, "必须是 EUR"):
                WORKFLOW.normalize_job(value, root / "wrong-currency")

    def test_duplicate_variants_are_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = self.base_input(root)
            value["variants"].append("B0F596K897-粉色-M")
            with self.assertRaisesRegex(ValueError, "重复"):
                WORKFLOW.normalize_job(value, root / "run")

    def test_variant_object_rejects_mismatched_raw_asin(self):
        with self.assertRaisesRegex(ValueError, "不一致"):
            WORKFLOW.normalize_variant({"asin": "B0F596K897", "raw": "B0GT99T4SQ-绿色"}, "IE")

    def test_review_job_resolves_model_attributes_without_changing_asins(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.base_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            reviewed = json.loads(json.dumps(job["variants"], ensure_ascii=False))
            for variant in reviewed:
                variant["unresolved_segments"] = []
                for attribute in variant["attributes"]:
                    if attribute["type"] == "audience_note":
                        attribute["canonical_value"] = "medium cats"
                        attribute["marketplace_value"] = "for medium-sized cats"
            review_path = root / "review.json"
            review_path.write_text(json.dumps({"variants": reviewed}, ensure_ascii=False), encoding="utf-8")
            args = Args()
            args.job = str(job_path)
            args.review = str(review_path)
            args.output = None
            result = WORKFLOW.review_job(args)
            self.assertTrue(result["ok"])
            self.assertFalse(WORKFLOW.load_json(job_path)["model_review_required"])

    def test_confirmation_is_bound_to_unchanged_job_and_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = self.ppc_ready_input(root)
            input_path = root / "input.json"
            input_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            prepare_args = Args()
            prepare_args.input = str(input_path)
            prepare_args.run_dir = str(root / "run")
            prepared = WORKFLOW.prepare(prepare_args)
            job_path = Path(prepared["job"])
            job = WORKFLOW.load_json(job_path)
            plan_path = root / "run" / "plan.json"
            plan_path.write_text(json.dumps({"status": "ready", "actions": [{"asin": asin, "action": "update"} for asin in job["target_asins"]]}), encoding="utf-8")
            ppc_plan, ppc_markdown, ppc_validation = self.write_valid_ppc_artifacts(root / "run", job)
            review, review_markdown, _ = self.write_manual_review_packet(
                root / "run", job_path, plan_path, job, ppc_plan, ppc_markdown, ppc_validation,
            )
            seal_args = Args()
            seal_args.job = str(job_path)
            seal_args.plan = str(plan_path)
            seal_args.review = str(review)
            seal_args.review_markdown = str(review_markdown)
            seal_args.output = str(root / "run" / "request.json")
            WORKFLOW.seal_plan(seal_args)
            confirm_args = Args()
            confirm_args.request = seal_args.output
            confirm_args.phrase = "确认执行"
            confirm_args.output = str(root / "run" / "confirmation.json")
            WORKFLOW.confirm(confirm_args)
            verify_args = Args()
            verify_args.confirmation = confirm_args.output
            self.assertTrue(WORKFLOW.verify_confirmation(verify_args)["ok"])
            plan_path.write_text(json.dumps({"status": "changed"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "发生变化"):
                WORKFLOW.verify_confirmation(verify_args)

    def test_report_validation_detects_foreign_variant_color(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.base_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            keyword_pool_path = root / "keyword-pool.json"
            keyword_pool_path.write_text(json.dumps({
                "keywords": [{"keyword": "cat window bed", "listing_eligible": True}],
            }), encoding="utf-8")
            keyword_validation_path = root / "keyword-validation.json"
            keyword_validation_path.write_text(json.dumps({
                "ok": True,
                "errors": [],
                "marketplace": job["marketplace"],
                "language": job["marketplace_language"],
                "pool": str(keyword_pool_path),
                "pool_sha256": WORKFLOW.sha256(keyword_pool_path),
            }), encoding="utf-8")
            keyword_pool_sha = WORKFLOW.sha256(keyword_pool_path)
            reports = []
            titles = {
                "B0F4NDR1ZB": "CareCooo Cat Window Bed, Suction Cups",
                "B0F596K897": "CareCooo Cat Window Bed, Suction Cups, Grey, M",
                "B0GT99T4SQ": "CareCooo Cat Window Bed, Suction Cups, Grey, Green, L",
            }
            for asin, title in titles.items():
                path = root / f"listing-optimization-report-{asin}.json"
                binding = self.original_listing_binding(f"Original title {asin}", asin=asin)
                sku_attributes = job["variants"][job["target_asins"].index(asin)]["expected_title_terms"]
                path.write_text(json.dumps({
                    "asin": asin, "marketplace": "IE",
                    "keyword_pool_sha256": keyword_pool_sha,
                    "keyword_priority": {"primary": ["cat window bed"]},
                    "keyword_coverage": [{"keyword": "cat window bed"}],
                    "keyword_gaps": [],
                    "listing": {"title": title, "bullets": ["Bullet"] * 5, "description": "Description", "backend_search_terms": "search terms"},
                    "title_options_2026": [{
                        "option": 1,
                        "title": title,
                        "item_highlights": "foldable frame, removable washable cover, for indoor cats",
                        "title_components": {
                            "brand": "CareCooo",
                            "core_product_phrase": "Cat Window Bed",
                            "differentiator": "Suction Cups",
                            "sku_attributes": sku_attributes,
                        },
                        "sku_attribute_placement": "title" if sku_attributes else "not_applicable",
                    }],
                    **binding,
                }), encoding="utf-8")
                reports.append(str(path))
            args = Args()
            args.job = str(job_path)
            args.keyword_validation = str(keyword_validation_path)
            args.reports = reports
            args.output = None
            with self.assertRaises(ValueError) as raised:
                WORKFLOW.validate_reports(args)
            self.assertIn("残留其他变体颜色", str(raised.exception))

    def test_mode_b_request_uses_only_minimal_allowed_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.base_input(root), root / "run")
            pool = {"keywords": [{"keyword": "cat window bed", "listing_eligible": True, "metrics": {"volume": 1000}}]}
            request = WORKFLOW.build_legacy_mode_b_request(
                job, pool, job["primary_asin"], "INV-B0F4NDR1ZB-20260801", "2026-08-01T00:00:00+00:00"
            )
            self.assertEqual(set(request["input_manifest"]), {
                "asin_target", "marketplace_language_tone", "core_keywords", "listing_eligible_keywords",
            })
            self.assertNotIn("selling_points", request)
            self.assertEqual(request["listing_eligible_keywords"][0]["metrics"], {"volume": 1000})

    def test_mode_b_request_rejects_upstream_listing_and_xlsm_fields(self):
        validator = WORKFLOW.load_legacy_handoff_validator()
        request = {
            "mode": "B", "asin": "B0F4NDR1ZB", "marketplace": "IE", "language": "en_IE",
            "tone": "Professional", "core_keywords": ["cat window bed"],
            "listing_eligible_keywords": [{"keyword": "cat window bed", "metrics": {"volume": 1000}}],
            "original_listing": {"title": "Forbidden"}, "xlsm": {"title": "Forbidden"},
            "variants": [], "competitor_asins": [], "selling_points": [], "ppc_campaign": {},
        }
        errors: list[str] = []
        validator.validate_mode_b_request(request, "B0F4NDR1ZB", errors)
        self.assertTrue(any("prohibited upstream inputs" in item for item in errors), errors)

    def test_review_packet_contains_every_pending_field_and_full_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            _, ppc_markdown, ppc_validation = self.write_valid_ppc_artifacts(root, job)
            ppc_validation_data = WORKFLOW.load_json(ppc_validation)
            keyword_pool_sha = ppc_validation_data["keyword_pool_sha256"]
            reports = []
            actions = []
            for index, asin in enumerate(job["target_asins"], 7):
                report_path = root / f"listing-optimization-report-{asin}.json"
                binding = self.original_listing_binding("Old", asin=asin)
                report_path.write_text(json.dumps({
                    "asin": asin, "marketplace": "IE",
                    "keyword_pool_sha256": keyword_pool_sha,
                    "listing": {"title": f"Long title {asin}", "bullets": [f"Bullet {number}" for number in range(1, 6)], "description": "Description", "backend_search_terms": "search terms"},
                    "title_options_generation": {
                        "reference_title": f"Long title {asin}",
                        "core_keyword_selection": {"status": "not_applicable", "reason": "测试数据"},
                        "reference_phrase_analysis": [],
                    },
                    "title_options_2026": [
                        {"option": 1, "rank": 1, "status": "recommended_for_current_upload", "score": 90, "title": f"Short title {asin}", "title_characters": len(f"Short title {asin}"), "item_highlights": "Highlights one", "item_highlights_characters": 14, "score_breakdown": {}, "title_components": {}, "sku_attribute_placement": "not_applicable", "sku_fit_evaluation": {}, "deduplication_notes": "测试说明", "core_strategy": "测试策略"},
                        {"option": 2, "rank": 2, "status": "alternate", "score": 85, "title": f"Alternate title 2 {asin}", "title_characters": len(f"Alternate title 2 {asin}"), "item_highlights": "Highlights two", "item_highlights_characters": 14, "score_breakdown": {}, "title_components": {}, "sku_attribute_placement": "not_applicable", "sku_fit_evaluation": {}, "deduplication_notes": "测试说明", "core_strategy": "测试策略"},
                        {"option": 3, "rank": 3, "status": "alternate", "score": 80, "title": f"Alternate title 3 {asin}", "title_characters": len(f"Alternate title 3 {asin}"), "item_highlights": "Highlights three", "item_highlights_characters": 16, "score_breakdown": {}, "title_components": {}, "sku_attribute_placement": "not_applicable", "sku_fit_evaluation": {}, "deduplication_notes": "测试说明", "core_strategy": "测试策略"},
                    ],
                    "diagnostic": {"tone": "Professional"},
                    "audit": {"score_before": "50/100", "score_after": "90/100", "dimensions": [{"dimension": "标题", "before": "5/15", "after": "14/15"}]},
                    "keyword_priority": {"primary": ["cat window bed"]},
                    "keyword_coverage": [{"keyword": "cat window bed", "status": "覆盖"}],
                    "keyword_gaps": [{"keyword": "cat perch", "priority": "中"}],
                    **binding,
                    "issues_fixed": ["修复标题"], "recommendations": ["核验图片"], "working_well": ["五点完整"],
                    "selling_point_notes": ["融入吸盘卖点"], "uploaded_keyword_file_summary": ["keywords.csv"],
                    "competitive_comparison": [{"dimension": "标题", "your_listing": "14/15"}],
                }, ensure_ascii=False), encoding="utf-8")
                reports.append(str(report_path))
                actions.append({
                    "asin": asin, "action": "update", "workbook": str(root / "template.xlsm"),
                    "sheet": "Template", "rows": [index], "station_evidence": ["marketplace_id", "filename"],
                    "fields": {"title": f"Short title {asin}", "item_highlight": "Highlights one", "title_mode": "短标题方案 1", "description": "Description", "bullets": [f"Bullet {number}" for number in range(1, 6)], "search_terms": "search terms"},
                    "planned_updates": [{"field": "title", "letter": "B", "hidden": False, "source_state": "已有内容，将覆盖", "action": "写入"}],
                })
            primary_report_path = Path(
                next(path for path in reports if job["primary_asin"] in path)
            )
            primary_report = WORKFLOW.load_json(primary_report_path)
            primary_report["rufus_qa"] = self.rufus_qa(keyword_pool_sha=keyword_pool_sha)
            primary_report_path.write_text(
                json.dumps(primary_report, ensure_ascii=False), encoding="utf-8"
            )
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps({"status": "ready", "actions": actions}, ensure_ascii=False), encoding="utf-8")
            listing_markdown = root / f"listing-optimization-plan-{job['primary_asin']}.md"
            listing_lines = [
                "# Listing 优化方案", "## Listing 优化审核报告", "评分",
                "## 关键词覆盖", "## 修改对比", "## 已修复问题", "## 建议",
                "## 原 Listing 中表现较好的部分",
            ]
            for action in actions:
                fields = action["fields"]
                listing_lines.extend([
                    action["asin"], fields["title"], fields["item_highlight"],
                    *fields["bullets"], fields["description"], fields["search_terms"],
                ])
            listing_markdown.write_text("\n\n".join(listing_lines) + "\n", encoding="utf-8")
            rufus_markdown = root / f"rufus-qa-plan-{job['primary_asin']}.md"
            rufus_markdown.write_text(
                WORKFLOW.load_rufus_qa_module().render_markdown(primary_report["rufus_qa"]),
                encoding="utf-8",
            )
            report_validation = self.write_report_validation(root, job, reports, keyword_pool_sha)
            rufus_validation = root / "rufus-qa-validation.json"
            rufus_args = Args()
            rufus_args.job = str(job_path)
            rufus_args.keyword_validation = ppc_validation_data["keyword_validation"]
            rufus_args.ppc_validation = str(ppc_validation)
            rufus_args.report = str(primary_report_path)
            rufus_args.markdown = str(rufus_markdown)
            rufus_args.output = str(rufus_validation)
            WORKFLOW.validate_rufus_plan(rufus_args)
            args = Args()
            args.job = str(job_path)
            args.keyword_validation = ppc_validation_data["keyword_validation"]
            args.plan = str(plan_path)
            args.reports = reports
            args.report_validation = str(report_validation)
            args.output = str(root / "review.json")
            args.markdown = str(root / "review.md")
            args.listing_markdown = str(listing_markdown)
            args.short_title_markdown = str(root / f"short-title-highlights-plan-{job['primary_asin']}.md")
            args.xlsm_markdown = str(root / "xlsm-replacement-plan.md")
            args.rufus_markdown = str(rufus_markdown)
            args.rufus_validation = str(rufus_validation)
            args.ppc_validation = str(ppc_validation)
            result = WORKFLOW.build_review_packet(args)
            self.assertTrue(result["ok"])
            packet = WORKFLOW.load_json(Path(args.output))
            self.assertEqual(len(packet["listings"]), len(job["target_asins"]))
            first = packet["listings"][0]
            self.assertEqual(first["pending_listing"]["item_name"], first["pending_listing"]["title"])
            self.assertEqual(len(first["pending_listing"]["bullets"]), 5)
            self.assertEqual(first["legacy_listing"]["title"], f"Long title {first['asin']}")
            self.assertNotEqual(first["legacy_listing"]["title"], first["pending_listing"]["title"])
            self.assertIn("dimensions", first["audit_report"]["audit"])
            markdown = Path(args.markdown).read_text(encoding="utf-8")
            listing_content = Path(args.listing_markdown).read_text(encoding="utf-8")
            self.assertEqual(result["pre_confirmation_files"], [
                str(Path(args.listing_markdown).resolve()), str(Path(args.short_title_markdown).resolve()),
                str(ppc_markdown.resolve()),
                str(Path(args.xlsm_markdown).resolve()),
                str(Path(args.rufus_markdown).resolve()),
            ])
            self.assertIn("# Listing 优化方案", markdown)
            self.assertIn("amazon-listing-optimization 输出（旧标题格式）", listing_content)
            self.assertIn(f"#### 优化后的旧格式标题\n\n```text\nLong title {first['asin']}", listing_content)
            self.assertIn("Bullet 5", markdown)
            self.assertIn("Backend Search Terms", markdown)
            self.assertIn("Listing 优化审核报告", markdown)
            self.assertIn("关键词覆盖", markdown)
            self.assertIn("# Rufus / Alexa for Shopping 商品 Q/A", markdown)
            for path in map(Path, result["pre_confirmation_files"]):
                self.assertTrue(path.is_file())
                self.assertIn(str(path.resolve()), markdown)
                self.assertIn(path.read_text(encoding="utf-8").rstrip(), markdown)

            changed_plan = WORKFLOW.load_json(plan_path)
            changed_plan["actions"][0]["fields"]["bullets"][0] = "Unbound rewritten bullet"
            plan_path.write_text(json.dumps(changed_plan, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "同步计划字段未绑定传统 Listing"):
                WORKFLOW.build_review_packet(args)
            plan_path.write_text(
                json.dumps({"status": "ready", "actions": actions}, ensure_ascii=False),
                encoding="utf-8",
            )

            rufus_markdown.write_text(
                rufus_markdown.read_text(encoding="utf-8") + "\n确认后新增内容\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Rufus Q/A 验证后的 Markdown 发生变化"):
                WORKFLOW.build_review_packet(args)

    def test_review_packet_blocks_when_audit_is_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            _, _, ppc_validation = self.write_valid_ppc_artifacts(root, job)
            ppc_validation_data = WORKFLOW.load_json(ppc_validation)
            reports = []
            actions = []
            for asin in job["target_asins"]:
                report_path = root / f"{asin}.json"
                report_path.write_text(json.dumps({
                    "asin": asin,
                    "marketplace": "IE",
                    "keyword_pool_sha256": ppc_validation_data["keyword_pool_sha256"],
                    **self.original_listing_binding(f"Original title {asin}", asin=asin),
                }), encoding="utf-8")
                reports.append(str(report_path))
                actions.append({"asin": asin, "action": "update", "fields": {"bullets": ["Bullet"] * 5}})
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps({"status": "ready", "actions": actions}), encoding="utf-8")
            report_validation = self.write_report_validation(
                root, job, reports, ppc_validation_data["keyword_pool_sha256"],
            )
            args = Args()
            args.job = str(job_path)
            args.keyword_validation = ppc_validation_data["keyword_validation"]
            args.plan = str(plan_path)
            args.reports = reports
            args.report_validation = str(report_validation)
            args.output = str(root / "review.json")
            args.markdown = str(root / "review.md")
            args.listing_markdown = str(root / f"listing-optimization-plan-{job['primary_asin']}.md")
            args.xlsm_markdown = str(root / "xlsm-replacement-plan.md")
            args.rufus_markdown = str(root / f"rufus-qa-plan-{job['primary_asin']}.md")
            args.ppc_validation = str(ppc_validation)
            with self.assertRaisesRegex(ValueError, "缺少完整审核报告字段"):
                WORKFLOW.build_review_packet(args)

    def test_seal_blocks_missing_preview_and_confirmation_expires_when_preview_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps({
                "status": "ready",
                "actions": [{"asin": asin, "action": "update"} for asin in job["target_asins"]],
            }), encoding="utf-8")
            ppc_plan, ppc_markdown, ppc_validation = self.write_valid_ppc_artifacts(root, job)
            review, review_markdown, files = self.write_manual_review_packet(
                root, job_path, plan_path, job, ppc_plan, ppc_markdown, ppc_validation,
            )
            packet = WORKFLOW.load_json(review)
            packet["pre_confirmation_deliverables"] = packet["pre_confirmation_deliverables"][:2]
            review.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
            seal_args = Args()
            seal_args.job = str(job_path)
            seal_args.plan = str(plan_path)
            seal_args.review = str(review)
            seal_args.review_markdown = str(review_markdown)
            seal_args.output = str(root / "request.json")
            with self.assertRaisesRegex(ValueError, "五个预确认文本文件"):
                WORKFLOW.seal_plan(seal_args)

            review, review_markdown, files = self.write_manual_review_packet(
                root, job_path, plan_path, job, ppc_plan, ppc_markdown, ppc_validation,
            )
            invalid_validation = WORKFLOW.load_json(ppc_validation)
            invalid_validation["ok"] = False
            invalid_validation["errors"] = ["validation failed"]
            ppc_validation.write_text(json.dumps(invalid_validation, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "PPC 方案尚未通过验证"):
                WORKFLOW.seal_plan(seal_args)

            ppc_plan, ppc_markdown, ppc_validation = self.write_valid_ppc_artifacts(root, job)
            review, review_markdown, files = self.write_manual_review_packet(
                root, job_path, plan_path, job, ppc_plan, ppc_markdown, ppc_validation,
            )
            WORKFLOW.seal_plan(seal_args)
            confirm_args = Args()
            confirm_args.request = seal_args.output
            confirm_args.phrase = "确认执行"
            confirm_args.output = str(root / "confirmation.json")
            WORKFLOW.confirm(confirm_args)
            sealed_review = WORKFLOW.load_json(review)
            keyword_pool_path = Path(sealed_review["keyword_pool"])
            original_keyword_pool = keyword_pool_path.read_text(encoding="utf-8")
            keyword_pool_path.write_text(original_keyword_pool + "\n", encoding="utf-8")
            verify_args = Args()
            verify_args.confirmation = confirm_args.output
            with self.assertRaisesRegex(ValueError, "统一关键词池|封存文件"):
                WORKFLOW.verify_confirmation(verify_args)
            keyword_pool_path.write_text(original_keyword_pool, encoding="utf-8")
            listing_content = files["listing_optimization"].read_text(encoding="utf-8")
            files["listing_optimization"].write_text("已修改", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "原确认已失效"):
                WORKFLOW.verify_confirmation(verify_args)
            files["listing_optimization"].write_text(listing_content, encoding="utf-8")
            primary_report = next(
                item for item in sealed_review["listings"] if item["asin"] == job["primary_asin"]
            )
            legacy_path = Path(
                WORKFLOW.load_json(Path(primary_report["report"]))["legacy_generation"]["artifact_path"]
            )
            legacy_content = legacy_path.read_text(encoding="utf-8")
            legacy_path.write_text(legacy_content + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "原确认已失效"):
                WORKFLOW.verify_confirmation(verify_args)

    def test_ppc_plan_validation_accepts_copy_ready_campaign_blueprint(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            keyword_validation, _keyword_pool, keyword_pool_sha = self.write_keyword_validation(root, job)
            plan = self.ppc_plan(job, keyword_pool_sha)
            plan_path = root / "ppc.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            markdown_path = root / "ppc.md"
            markdown_path.write_text(self.ppc_markdown(plan), encoding="utf-8")
            args = Args()
            args.job = str(job_path)
            args.keyword_validation = str(keyword_validation)
            args.plan = str(plan_path)
            args.markdown = str(markdown_path)
            args.output = str(root / "validation.json")
            result = WORKFLOW.validate_ppc_plan(args)
            self.assertTrue(result["ok"])
            self.assertEqual(result["copy_block_counts"]["manual_exact_keywords"], 2)
            self.assertIn("product_targeting", result["campaign_types"])

    def test_prepare_ppc_source_packet_contains_only_fact_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            keyword_validation, _pool, _sha = self.write_keyword_validation(root, job)
            report_path = root / "listing-optimization-report-B0F4NDR1ZB.json"
            report_path.write_text(json.dumps({
                "asin": job["primary_asin"], "marketplace": job["marketplace"],
                "legacy_generation": {"legacy_listing": {"title": "Cat Window Bed", "bullets": [], "description": "", "backend_search_terms": ""}},
                "title_options_2026": [{
                    "status": "recommended_for_current_upload", "title": "CareCooo Cat Window Bed",
                    "item_highlights": "Suction Cups",
                    "title_components": {"brand": "CareCooo", "core_product_phrase": "Cat Window Bed"},
                }],
            }, ensure_ascii=False), encoding="utf-8")
            args = Args()
            args.job = str(job_path)
            args.keyword_validation = str(keyword_validation)
            args.report = str(report_path)
            args.output = str(root / "ppc-mode-a-source-packet-B0F4NDR1ZB.json")
            result = WORKFLOW.build_ppc_source_packet(args)
            packet = WORKFLOW.load_json(Path(result["packet"]))
            self.assertFalse(WORKFLOW.ppc_packet_has_strategy(packet))
            self.assertEqual(packet["mode"], "A")
            self.assertFalse(packet["historical_ad_data"]["included"])
            self.assertEqual(packet["financial"]["conversion_rate"]["value"], None)
            self.assertEqual(packet["financial_defaults_applied"], job["ppc_campaign"]["defaults_applied"])
            self.assertEqual(packet["product_context"]["campaign_label"], "CareCooo Cat Window Bed")

    def test_ppc_provenance_and_no_conversion_rate_rejects_numeric_bid(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            keyword_validation, _pool, keyword_pool_sha = self.write_keyword_validation(root, job)
            packet_path = root / "ppc-mode-a-source-packet-B0F4NDR1ZB.json"
            plan = self.ppc_plan(job, keyword_pool_sha)
            plan["financial_framework"]["defaults_applied"] = job["ppc_campaign"]["defaults_applied"]
            financial_inputs = {
                "selling_price": {"value": 39.99, "source": "user_provided", "reason": "用户提供售价"},
                "monthly_ad_budget": {"value": 900, "source": "user_provided", "reason": "用户提供预算"},
                "break_even_acos": {"value": plan["financial_framework"]["break_even_acos"], "source": "user_provided", "reason": "用户提供成本"},
                "conversion_rate": {"value": None, "source": "not_provided", "reason": "未提供转化率"},
            }
            plan["financial_framework"]["financial_inputs"] = financial_inputs
            packet_path.write_text(json.dumps({
                "mode": "A", "historical_ad_data": {"included": False},
                "financial": financial_inputs,
                "financial_defaults_applied": job["ppc_campaign"]["defaults_applied"],
                "product_context": {
                    "campaign_label": "Cat Window Bed",
                    "recommended_2026_title": "CareCooo Cat Window Bed",
                },
            }, ensure_ascii=False), encoding="utf-8")
            invocation_id = "PPC-INVOCATION-20260802-001"
            raw_path = root / "ppc-skill-raw-output-B0F4NDR1ZB.md"
            request_path = root / "ppc-skill-request-B0F4NDR1ZB.json"
            plan["generation_provenance"] = {
                "source_skill": WORKFLOW.PPC_SOURCE_SKILL,
                "source_skill_path": WORKFLOW.PPC_SOURCE_SKILL_PATH,
                "source_skill_sha256": WORKFLOW.sha256(Path(WORKFLOW.PPC_SOURCE_SKILL_PATH)),
                "invocation_id": invocation_id,
                "source_packet_path": str(packet_path.resolve()),
                "source_packet_sha256": WORKFLOW.sha256(packet_path),
                "raw_output_path": str(raw_path.resolve()),
                "raw_output_sha256": "",
            }
            canonical = dict(plan)
            canonical.pop("generation_provenance")
            raw_path.write_text(json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            plan["generation_provenance"]["raw_output_sha256"] = WORKFLOW.sha256(raw_path)
            request_path.write_text(json.dumps({
                "source_skill": WORKFLOW.PPC_SOURCE_SKILL,
                "source_skill_path": WORKFLOW.PPC_SOURCE_SKILL_PATH,
                "mode": "A", "invocation_id": invocation_id,
                "source_packet_path": str(packet_path.resolve()),
                "source_packet_sha256": WORKFLOW.sha256(packet_path),
            }, ensure_ascii=False), encoding="utf-8")
            plan_path = root / "ppc.json"
            markdown_path = root / "ppc.md"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            markdown_path.write_text(self.ppc_markdown(plan), encoding="utf-8")
            args = Args()
            args.job, args.keyword_validation = str(job_path), str(keyword_validation)
            args.plan, args.markdown = str(plan_path), str(markdown_path)
            args.source_packet, args.request, args.raw_output = str(packet_path), str(request_path), str(raw_path)
            args.output = None
            self.assertTrue(WORKFLOW.validate_ppc_plan(args)["ok"])
            plan["campaigns"][0]["default_bid"] = 0.3
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "不得输出金额 CPC/出价"):
                WORKFLOW.validate_ppc_plan(args)

    def test_ppc_plan_validation_blocks_missing_cross_campaign_negatives(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            keyword_validation, _keyword_pool, keyword_pool_sha = self.write_keyword_validation(root, job)
            plan = self.ppc_plan(job, keyword_pool_sha)
            plan["copy_blocks"]["auto_negative_exact_keywords"] = ["cat window bed"]
            plan_path = root / "ppc.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            markdown_path = root / "ppc.md"
            markdown_path.write_text(self.ppc_markdown(plan), encoding="utf-8")
            args = Args()
            args.job = str(job_path)
            args.keyword_validation = str(keyword_validation)
            args.plan = str(plan_path)
            args.markdown = str(markdown_path)
            args.output = None
            with self.assertRaisesRegex(ValueError, "Auto Negative Exact"):
                WORKFLOW.validate_ppc_plan(args)

    def test_ppc_plan_rejects_positive_keywords_outside_unified_pool(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            (root / "job.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            keyword_validation, _keyword_pool, keyword_pool_sha = self.write_keyword_validation(root, job)
            plan = self.ppc_plan(job, keyword_pool_sha)
            plan["copy_blocks"]["manual_broad_keywords"].append("invented traffic keyword")
            plan_path = root / "ppc.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            markdown_path = root / "ppc.md"
            markdown_path.write_text(self.ppc_markdown(plan), encoding="utf-8")
            args = Args()
            args.job = str(root / "job.json")
            args.keyword_validation = str(keyword_validation)
            args.plan = str(plan_path)
            args.markdown = str(markdown_path)
            args.output = None
            with self.assertRaisesRegex(ValueError, "ppc_eligible"):
                WORKFLOW.validate_ppc_plan(args)

    def test_ppc_plan_carries_default_metadata_and_assumptions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            value = self.base_input(root)
            value["ppc_campaign"] = {"selling_price": 39.99}
            job = WORKFLOW.normalize_job(value, root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            keyword_validation, _keyword_pool, keyword_pool_sha = self.write_keyword_validation(root, job)
            plan = self.ppc_plan(job, keyword_pool_sha)
            plan["financial_framework"].update({
                "monthly_ad_budget": 600,
                "break_even_acos": 0.4,
                "target_acos_launch": 0.4,
                "target_acos_mature": 0.3,
                "assumptions": ["月度预算与盈亏平衡 ACoS 使用技能默认值。"],
                "defaults_applied": job["ppc_campaign"]["defaults_applied"],
            })
            plan["data_quality"]["financial_confidence"] = "assumption_limited"
            plan["data_quality"]["financial_limitations"] = "月度预算与盈亏平衡 ACoS 使用默认值，不能视为真实利润预测。"
            plan_path = root / "ppc.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            markdown_path = root / "ppc.md"
            markdown_path.write_text(self.ppc_markdown(plan), encoding="utf-8")
            args = Args()
            args.job = str(job_path)
            args.keyword_validation = str(keyword_validation)
            args.plan = str(plan_path)
            args.markdown = str(markdown_path)
            args.output = None
            self.assertTrue(WORKFLOW.validate_ppc_plan(args)["ok"])

            del plan["financial_framework"]["defaults_applied"]
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "defaults_applied"):
                WORKFLOW.validate_ppc_plan(args)

    def test_ppc_plan_rejects_non_chinese_explanatory_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            keyword_validation, _keyword_pool, keyword_pool_sha = self.write_keyword_validation(root, job)
            plan = self.ppc_plan(job, keyword_pool_sha)
            plan["risk_notes"] = ["Use Amazon suggested bid when available"]
            plan_path = root / "ppc.json"
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            markdown_path = root / "ppc.md"
            markdown_path.write_text(self.ppc_markdown(plan), encoding="utf-8")
            args = Args()
            args.job = str(job_path)
            args.keyword_validation = str(keyword_validation)
            args.plan = str(plan_path)
            args.markdown = str(markdown_path)
            args.output = None
            with self.assertRaisesRegex(ValueError, "说明字段 risk_notes"):
                WORKFLOW.validate_ppc_plan(args)

            plan["risk_notes"] = ["有建议竞价时使用 Amazon Suggested Bid"]
            plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
            markdown = self.ppc_markdown(plan).replace("# PPC 广告方案", "# PPC Campaign Blueprint")
            markdown_path.write_text(markdown, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Markdown.*说明文字必须使用中文"):
                WORKFLOW.validate_ppc_plan(args)

    def test_validate_rufus_plan_requires_ppc_and_generates_markdown(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.ppc_ready_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            keyword_validation, _keyword_pool, keyword_pool_sha = self.write_keyword_validation(root, job)
            report_path = root / "listing-report.json"
            report_path.write_text(json.dumps({
                "asin": job["primary_asin"],
                "marketplace": "IE",
                "keyword_pool_sha256": keyword_pool_sha,
                "rufus_qa": self.rufus_qa(keyword_pool_sha=keyword_pool_sha),
            }, ensure_ascii=False), encoding="utf-8")
            ppc_validation_path = root / "ppc-validation.json"
            args = Args()
            args.job = str(job_path)
            args.keyword_validation = str(keyword_validation)
            args.ppc_validation = str(ppc_validation_path)
            args.report = str(report_path)
            args.markdown = str(root / f"rufus-qa-plan-{job['primary_asin']}.md")
            args.output = str(root / "qa-validation.json")

            ppc_validation_path.write_text(json.dumps({"ok": False, "errors": ["failed"]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "PPC 方案尚未通过验证"):
                WORKFLOW.validate_rufus_plan(args)

            _ppc_plan, _ppc_markdown, ppc_validation_path = self.write_valid_ppc_artifacts(root, job)
            args.ppc_validation = str(ppc_validation_path)
            invalid_qa = self.rufus_qa(keyword_pool_sha=keyword_pool_sha)
            invalid_qa["items"][0]["keyword_refs"] = ["KW-999"]
            report = WORKFLOW.load_json(report_path)
            report["rufus_qa"] = invalid_qa
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "非 qa_eligible"):
                WORKFLOW.validate_rufus_plan(args)
            report["rufus_qa"] = self.rufus_qa(keyword_pool_sha=keyword_pool_sha)
            report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            result = WORKFLOW.validate_rufus_plan(args)
            self.assertTrue(result["ok"])
            self.assertTrue(Path(args.markdown).is_file())
            self.assertTrue(Path(args.output).is_file())
            self.assertEqual(result["report_sha256"], WORKFLOW.sha256(report_path))
            self.assertIn("Rufus / Alexa for Shopping", Path(args.markdown).read_text(encoding="utf-8"))

    def test_skill_has_no_runtime_listing2_dependency_or_xlsx_finalizer(self):
        skill_root = Path(__file__).parents[1]
        workflow = (skill_root / "scripts" / "workflow.py").read_text(encoding="utf-8")
        self.assertNotIn("amazon-listing-optimization2", workflow)
        self.assertNotIn("finalize-rufus-qa", workflow)
        self.assertNotIn("write-listing-report-xlsx", workflow)

    def test_status_machine_requires_ppc_then_qa_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            status_path = root / "status.json"
            status_path.write_text(json.dumps({"phase": "sync_planned", "artifacts": {}}), encoding="utf-8")
            args = Args()
            args.status = str(status_path)
            args.phase = "ppc_ready"
            args.artifact = []
            with self.assertRaisesRegex(ValueError, "缺少验证文件"):
                WORKFLOW.transition(args)

            ppc_validation = root / "ppc-validation.json"
            ppc_validation.write_text(json.dumps({"ok": True, "errors": []}), encoding="utf-8")
            args.artifact = [f"ppc_validation={ppc_validation}"]
            self.assertEqual(WORKFLOW.transition(args)["phase"], "ppc_ready")

            qa_validation = root / "qa-validation.json"
            qa_validation.write_text(json.dumps({"ok": True, "errors": []}), encoding="utf-8")
            args.phase = "qa_ready"
            args.artifact = [f"rufus_qa_validation={qa_validation}"]
            self.assertEqual(WORKFLOW.transition(args)["phase"], "qa_ready")

            for phase in ("awaiting_confirmation", "confirmed", "applied"):
                args.phase = phase
                args.artifact = []
                self.assertEqual(WORKFLOW.transition(args)["phase"], phase)

            delivery_validation = root / "delivery-validation.json"
            delivery_validation.write_text(json.dumps({"ok": True, "errors": []}), encoding="utf-8")
            args.phase = "verified"
            args.artifact = [f"delivery_validation={delivery_validation}"]
            self.assertEqual(WORKFLOW.transition(args)["phase"], "verified")

            args.phase = "completed"
            args.artifact = []
            self.assertEqual(WORKFLOW.transition(args)["phase"], "completed")

    def test_status_machine_requires_validated_keyword_pool(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            job = WORKFLOW.normalize_job(self.base_input(root), root / "run")
            job_path = root / "job.json"
            job_path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
            status_path = root / "status.json"
            status_path.write_text(json.dumps({
                "phase": "prepared", "artifacts": {"job": str(job_path)},
            }), encoding="utf-8")
            args = Args()
            args.status = str(status_path)
            args.phase = "keywords_ready"
            args.artifact = []
            with self.assertRaisesRegex(ValueError, "keyword_validation"):
                WORKFLOW.transition(args)

            _pool, validation_path, _result = self.write_valid_keyword_pool(root, job, source_count=10)
            args.artifact = [f"keyword_validation={validation_path}"]
            self.assertEqual(WORKFLOW.transition(args)["phase"], "keywords_ready")


if __name__ == "__main__":
    unittest.main()
