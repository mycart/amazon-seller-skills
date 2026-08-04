import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "legacy_handoff_v2", ROOT / "scripts" / "validate-legacy-handoff.py"
)
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class TitleAllocationV2Tests(unittest.TestCase):
    @staticmethod
    def validate_archived(report):
        return VALIDATOR.validate_report(report, allow_legacy_title_method=True)

    def phrase(
        self,
        phrase_id,
        source_text,
        source_order,
        roles,
        priority,
        fact_ref,
        *,
        keyword_refs=None,
        selling_point_refs=None,
        differentiation_refs=None,
        dual_value_rank=0,
        decision_factor="other",
        decision_value="medium",
        semantic_group_id="",
        semantic_relation="none",
    ):
        return {
            "id": phrase_id,
            "source_text": source_text,
            "normalized_text": source_text.casefold(),
            "source_order": source_order,
            "roles": roles,
            "keyword_refs": keyword_refs or [],
            "selling_point_refs": selling_point_refs or [],
            "differentiation_refs": differentiation_refs or [],
            "fact_refs": [fact_ref],
            "evidence_status": "verified",
            "priority": priority,
            "dual_value_rank": dual_value_rank,
            "decision_factor": decision_factor,
            "decision_value": decision_value,
            "decision_reason": "根据已验证商品事实和购买决策价值确定优先级",
            "semantic_group_id": semantic_group_id,
            "semantic_relation": semantic_relation,
        }

    def realization(self, placement, text, reuse_type, fact_ref, operations=None, added=None):
        return {
            "placement": placement,
            "text": text,
            "reuse_type": reuse_type,
            "rewrite_operations": operations or [],
            "added_tokens": added or [],
            "fact_refs": [fact_ref],
            "reason": "沿用并分配旧标题中的已验证商品表达",
        }

    def report(self, dual_text="Waterproof", cross_field=False, move_sku=False):
        legacy_title = (
            f"FlexiCo Travel Mat {dual_text}, Blue, 60 x 40 cm, Foldable, Storage Bag"
        )
        phrases = [
            self.phrase(
                "RP-01", "FlexiCo", 1, ["brand"], "identity", "FACT-BRAND",
                decision_factor="identity", decision_value="required",
            ),
            self.phrase(
                "RP-02", "Travel Mat", 2, ["core_product"], "identity", "FACT-PRODUCT",
                keyword_refs=["KW-TRAVEL-MAT"], decision_factor="identity",
                decision_value="required",
            ),
            self.phrase(
                "RP-03", dual_text, 3, ["differentiator", "performance"],
                "dual_value_differentiator", "FACT-DUAL",
                keyword_refs=["KW-DUAL"], selling_point_refs=["SP-DUAL"],
                differentiation_refs=["DIFF-DUAL"], dual_value_rank=1,
                decision_factor="performance", decision_value="high",
            ),
            self.phrase(
                "RP-04", "Blue", 4, ["sku_attribute"], "sku_attribute", "FACT-COLOR",
                decision_factor="variant", decision_value="required",
            ),
            self.phrase(
                "RP-05", "60 x 40 cm", 5, ["sku_attribute", "specification"],
                "sku_attribute", "FACT-SIZE", decision_factor="dimensions",
                decision_value="required",
            ),
            self.phrase(
                "RP-06", "Foldable", 6, ["function"], "selling_point_only",
                "FACT-FOLD", selling_point_refs=["SP-FOLD"],
                decision_factor="function", decision_value="medium",
            ),
            self.phrase(
                "RP-07", "Storage Bag", 7, ["included_accessory"],
                "verified_spec_or_differentiator", "FACT-BAG",
                decision_factor="accessory", decision_value="medium",
            ),
        ]

        if cross_field:
            title_dual = "Velcro"
            dual_realizations = [
                self.realization(
                    "title", "Velcro", "controlled_rewrite", "FACT-DUAL", ["retain_anchor"]
                ),
                self.realization(
                    "item_highlights", dual_text, "verbatim", "FACT-DUAL"
                ),
            ]
        else:
            title_dual = dual_text
            dual_realizations = [
                self.realization("title", dual_text, "verbatim", "FACT-DUAL")
            ]

        priority_base = f"FlexiCo Travel Mat {title_dual}"
        sku_attributes = ["Blue", "60 x 40 cm"]
        with_sku = " ".join([priority_base, *sku_attributes])
        calculated_move = len(with_sku) > 75
        move_sku = move_sku or calculated_move
        if move_sku:
            title = priority_base
            highlights_parts = ["Blue", "60x40cm"]
            placement = "item_highlights"
            sku_reason = "保留更高优先级双重差异化词后完整SKU属性组超过75字符"
        else:
            title = f"{priority_base}, Blue, 60x40cm"
            highlights_parts = []
            placement = "title"
            sku_reason = ""
        if cross_field:
            highlights_parts.append(dual_text)
        highlights_parts.extend(["Foldable", "storage bag"])
        highlights = ", ".join(highlights_parts)

        def allocation(phrase_id, realizations):
            return {
                "phrase_id": phrase_id,
                "status": "used",
                "realizations": realizations,
                "reason_code": "retained",
                "reason": "按证据和标题优先级分配该参考短语",
            }

        allocations = [
            allocation("RP-01", [self.realization("title", "FlexiCo", "verbatim", "FACT-BRAND")]),
            allocation("RP-02", [self.realization("title", "Travel Mat", "verbatim", "FACT-PRODUCT")]),
            allocation("RP-03", dual_realizations),
            allocation(
                "RP-04", [self.realization(placement, "Blue", "verbatim", "FACT-COLOR")]
            ),
            allocation(
                "RP-05",
                [self.realization(placement, "60x40cm", "normalized", "FACT-SIZE", ["compact_unit"])],
            ),
            allocation(
                "RP-06", [self.realization("item_highlights", "Foldable", "verbatim", "FACT-FOLD")]
            ),
            allocation(
                "RP-07",
                [self.realization(
                    "item_highlights", "storage bag", "normalized", "FACT-BAG", ["normalize_case"]
                )],
            ),
        ]
        option = {
            "option": 1,
            "rank": 1,
            "status": "recommended_for_current_upload",
            "title": title,
            "item_highlights": highlights,
            "title_components": {
                "brand": "FlexiCo",
                "core_product_phrase": "Travel Mat",
                "differentiator": title_dual,
                "sku_attributes": sku_attributes,
            },
            "sku_attribute_placement": placement,
            "sku_move_reason": sku_reason,
            "sku_fit_evaluation": {
                "priority_base_title": priority_base,
                "sku_attributes": sku_attributes,
                "base_characters": len(priority_base),
                "with_sku_characters": len(with_sku),
                "limit": 75,
                "fits": not calculated_move,
                "final_placement": placement,
                "reason": "先保留品牌、品类和双重差异化词，再计算完整SKU属性组",
            },
            "reference_phrase_allocation": allocations,
            "additional_verified_phrases": [],
        }

        manifest = {
            section: {
                "provided": False,
                "status": "not_provided",
                "note": "本测试未提供该输入来源",
            }
            for section in VALIDATOR.INPUT_SECTIONS
        }
        manifest["marketplace_language_tone"] = {
            "provided": True,
            "status": "used",
            "data": {"marketplace": "US", "language": "en_US", "tone": "Professional"},
            "note": "已提供测试站点和语言",
        }
        manifest["product_facts_and_selling_points"] = {
            "provided": True,
            "status": "used",
            "data": ["Waterproof", "Blue", "60 x 40 cm"],
            "note": "已提供测试商品事实",
        }
        legacy_listing = {
            "title": legacy_title,
            "bullets": [f"Bullet {index}" for index in range(1, 6)],
            "description": "Verified test description.",
            "backend_search_terms": "travel mat waterproof foldable storage bag",
        }
        return {
            "asin": "NEW-LISTING",
            "mode": "A",
            "marketplace": "US",
            "generation_sequence": ["evidence_collection", "legacy_listing", "title_options_2026"],
            "listing_generation_source": "amazon-listing-optimization",
            "legacy_generation": {
                "source_skill": "amazon-listing-optimization",
                "source_skill_path": "/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md",
                "source_skill_sha256": VALIDATOR.file_sha256(
                    Path("/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md")
                ),
                "artifact_path": "/tmp/legacy-listing-result-NEW-LISTING.json",
                "invocation_id": "INV-NEW-LISTING-20260731T100000",
                "started_at": "2026-07-31T09:59:00+08:00",
                "request_path": "/tmp/legacy-listing-request-NEW-LISTING.json",
                "request_sha256": "0" * 64,
                "raw_output_path": "/tmp/legacy-listing-raw-output-NEW-LISTING.md",
                "raw_output_sha256": "0" * 64,
                "mode": "A",
                "status": "complete",
                "completed_at": "2026-07-31T10:00:00+08:00",
                "input_manifest": manifest,
                "legacy_listing": legacy_listing,
                "keyword_priority": {},
                "keyword_coverage": [],
                "keyword_gaps": [],
                "limitations": [],
            },
            "listing": copy.deepcopy(legacy_listing),
            "title_options_generation": {
                "started_at": "2026-07-31T10:01:00+08:00",
                "reference_title": legacy_title,
                "method": "legacy_reference_phrase_allocation_v2",
                "reference_phrase_analysis": phrases,
            },
            "title_options_2026": [copy.deepcopy(option) for _ in range(3)],
            "diagnostic": {},
        }

    def enable_v3_core_keyword(self, report, traffic_type="metric"):
        if traffic_type == "metric":
            traffic_status = "verified_metric"
            traffic_evidence = [{
                "type": "metric",
                "source": "uploaded_keyword_file",
                "metric": "search_volume",
                "value": 1200,
            }]
        else:
            traffic_status = "user_confirmed"
            traffic_evidence = [{"type": "user_explicit", "source": "user"}]
        report["title_options_generation"]["method"] = (
            "legacy_reference_phrase_allocation_v4"
        )
        report["title_options_generation"]["core_keyword_selection"] = {
            "status": "selected",
            "selection_rule": "first_eligible_user_input",
            "preservation_mode": "all_tokens_same_order_normalization_only",
            "selected_keyword": "Travel Mat",
            "reason": "按用户输入顺序选择第一个符合品类且有流量证据的核心关键词",
            "candidates": [
                {
                    "keyword": "Travel Mat",
                    "input_order": 1,
                    "marketplace_language_match": True,
                    "category_match": True,
                    "category_fact_refs": ["FACT-PRODUCT"],
                    "listing_eligible": True,
                    "traffic_status": traffic_status,
                    "traffic_evidence": traffic_evidence,
                    "eligible": True,
                    "reason": "该词符合商品品类、目标语言和流量词要求",
                },
                {
                    "keyword": "Portable Ground Mat",
                    "input_order": 2,
                    "marketplace_language_match": True,
                    "category_match": True,
                    "category_fact_refs": ["FACT-PRODUCT"],
                    "listing_eligible": True,
                    "traffic_status": "user_confirmed",
                    "traffic_evidence": [{"type": "user_explicit", "source": "user"}],
                    "eligible": True,
                    "reason": "该词同样合格但用户输入顺序靠后",
                },
            ],
        }
        report["title_options_generation"]["title_pair_fact_pool"] = [
            {"id": "TPF-01", "text": "Waterproof", "fact_refs": ["FACT-DUAL"],
             "keyword_refs": ["KW-DUAL"], "selling_point_refs": ["SP-DUAL"],
             "decision_factor": "performance", "decision_value": "high", "character_cost": 10,
             "highlight_candidate": {"text": "Waterproof", "fact_refs": ["FACT-DUAL"], "character_cost": 10,
                                     "title_information_gain": "该性能词在未进入标题时可作为亮点补充事实。"}},
            {"id": "TPF-02", "text": "Foldable", "fact_refs": ["FACT-FOLD"],
             "keyword_refs": [], "selling_point_refs": ["SP-FOLD"],
             "decision_factor": "function", "decision_value": "high", "character_cost": 8,
             "highlight_candidate": {"text": "Foldable", "fact_refs": ["FACT-FOLD"], "character_cost": 8,
                                     "title_information_gain": "该功能词可在亮点中补充独立购买决策信息。"}},
            {"id": "TPF-03", "text": "storage bag", "fact_refs": ["FACT-BAG"],
             "keyword_refs": [], "selling_point_refs": [],
             "decision_factor": "accessory", "decision_value": "medium", "character_cost": 11},
        ]
        strategies = [
            ("search_identity", "RP-03", "FACT-DUAL", 100),
            ("purchase_decision", "RP-06", "FACT-FOLD", 99),
            ("use_context", "RP-07", "FACT-BAG", 98),
        ]
        for index, (strategy, focus_id, focus_fact, score) in enumerate(strategies):
            option = report["title_options_2026"][index]
            option["option"] = index + 1
            option["rank"] = index + 1
            option["status"] = "recommended_for_current_upload" if index == 0 else "alternate"
            option["generation_strategy"] = strategy
            option["strategy_focus_phrase_ids"] = [focus_id]
            option["quality_rationale"] = "以已验证事实建立与其他方案不同的购买判断重点"
            option["evidence_coverage"] = ["FACT-PRODUCT", focus_fact]
            option["quality_assessment"] = {
                "evidence_and_policy": 35,
                "identity_and_variant_completeness": 20,
                "pair_information_coverage": 20,
                "keyword_and_search_intent": 15,
                "natural_language_and_mobile_readability": score - 90,
                "total": score,
            }
            option["title_pair_coverage_audit"] = [
                {"fact_id": "TPF-01", "placement": "title", "text": "Waterproof",
                 "reason": "标题保留已验证的核心性能信息"},
                {"fact_id": "TPF-02", "placement": "item_highlights", "text": "Foldable",
                 "reason": "亮点补充可折叠这一购买决策信息"},
                {"fact_id": "TPF-03", "placement": "item_highlights", "text": "storage bag",
                 "reason": "亮点补充收纳配件这一购买决策信息"},
            ]
            if strategy == "purchase_decision":
                option["title"] += ", Foldable"
                option["item_highlights"] = option["item_highlights"].replace(
                    "Foldable, ", ""
                )
                option["reference_phrase_allocation"][5]["realizations"] = [
                    self.realization("title", "Foldable", "verbatim", "FACT-FOLD")
                ]
            elif strategy == "use_context":
                option["title"] += ", storage bag"
                option["item_highlights"] = option["item_highlights"].replace(
                    ", storage bag", ""
                )
                option["reference_phrase_allocation"][6]["realizations"] = [
                    self.realization(
                        "title", "storage bag", "normalized", "FACT-BAG", ["normalize_case"]
                    )
                ]
            for row in option["title_pair_coverage_audit"]:
                if row["text"].casefold() in option["title"].casefold():
                    row["placement"] = "title"
            candidates = report["title_options_generation"]["title_pair_fact_pool"]
            available = [
                fact for fact in candidates
                if "highlight_candidate" in fact
                and fact["highlight_candidate"]["text"].casefold() not in option["title"].casefold()
            ]
            usable = sum(fact["highlight_candidate"]["character_cost"] for fact in available)
            if available:
                usable += 2 * (len(available) - 1)
            option["highlight_capacity"] = {
                "available_highlight_candidate_ids": [fact["id"] for fact in available],
                "usable_highlight_characters": usable,
                "target_highlight_characters": min(100, usable) if len(available) >= 3 and usable >= 100 else usable,
                "actual_highlight_characters": len(option["item_highlights"]),
                "capacity_status": "achieved",
                "unallocated_candidates": [],
            }
        return report

    def test_v2_dual_value_differentiator_precedes_sku_and_validates(self):
        report = self.report()
        result = self.validate_archived(report)
        self.assertTrue(result["ok"], result["errors"])
        phrase = report["title_options_generation"]["reference_phrase_analysis"][2]
        self.assertEqual(
            VALIDATOR.expected_priority(
                phrase, set(phrase["roles"]), VALIDATOR.REFERENCE_METHOD_V2
            ),
            "dual_value_differentiator",
        )

    def test_v3_preserves_first_eligible_core_traffic_keyword(self):
        for traffic_type in ("metric", "user_explicit"):
            with self.subTest(traffic_type=traffic_type):
                report = self.enable_v3_core_keyword(self.report(), traffic_type)
                result = VALIDATOR.validate_report(report)
                self.assertTrue(result["ok"], result["errors"])

        wrong_selection = self.enable_v3_core_keyword(self.report())
        wrong_selection["title_options_generation"]["core_keyword_selection"][
            "selected_keyword"
        ] = "Portable Ground Mat"
        result = VALIDATOR.validate_report(wrong_selection)
        self.assertFalse(result["ok"])
        self.assertTrue(any("first eligible" in error for error in result["errors"]))

    def test_v3_rejects_shortened_reordered_or_inflected_core_keyword(self):
        for replacement in ("Travel", "Mat Travel", "Travel Mats"):
            with self.subTest(replacement=replacement):
                report = self.enable_v3_core_keyword(self.report())
                for option in report["title_options_2026"]:
                    option["title"] = option["title"].replace("Travel Mat", replacement)
                    option["title_components"]["core_product_phrase"] = replacement
                result = VALIDATOR.validate_report(report)
                self.assertFalse(result["ok"])
                self.assertTrue(
                    any("required core keyword" in error for error in result["errors"]),
                    result["errors"],
                )

    def test_v3_rejects_candidates_that_only_change_presentation(self):
        report = self.enable_v3_core_keyword(self.report())
        duplicate = report["title_options_2026"][1]
        first = report["title_options_2026"][0]
        duplicate["title"] = first["title"].upper()
        duplicate["item_highlights"] = first["item_highlights"].replace(", ", "; ")
        duplicate["strategy_focus_phrase_ids"] = ["RP-06"]
        result = VALIDATOR.validate_report(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("materially identical" in error for error in result["errors"]))

    def test_v4_requires_complete_pair_coverage_and_rank_order(self):
        report = self.enable_v3_core_keyword(self.report())
        report["title_options_2026"][0]["title_pair_coverage_audit"].pop()
        report["title_options_2026"][2]["rank"] = 2
        result = VALIDATOR.validate_report(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("must allocate every title-pair fact" in error for error in result["errors"]))
        self.assertTrue(any("use each rank exactly once" in error for error in result["errors"]))

    def test_v3_is_archive_only_after_v4_upgrade(self):
        report = self.enable_v3_core_keyword(self.report())
        report["title_options_generation"]["method"] = "legacy_reference_phrase_allocation_v3"
        result = VALIDATOR.validate_report(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("archive-read-only" in error for error in result["errors"]))
        result = self.validate_archived(report)
        self.assertTrue(result["ok"], result["errors"])

    def test_keyword_and_selling_point_without_differentiation_is_plain_dual_value(self):
        phrase = {
            "keyword_refs": ["KW-01"],
            "selling_point_refs": ["SP-01"],
            "differentiation_refs": [],
            "fact_refs": ["FACT-01"],
        }
        self.assertEqual(
            VALIDATOR.expected_priority(
                phrase, {"function"}, VALIDATOR.REFERENCE_METHOD_V2
            ),
            "dual_value",
        )

    def test_sku_moves_only_after_reserving_higher_priority_phrase(self):
        report = self.report(
            dual_text="Self-Adhesive Industrial Velcro Mounting System",
            move_sku=True,
        )
        result = self.validate_archived(report)
        self.assertTrue(result["ok"], result["errors"])
        option = report["title_options_2026"][0]
        self.assertEqual(option["sku_attribute_placement"], "item_highlights")
        self.assertIn("Self-Adhesive Industrial Velcro", option["title"])
        self.assertIn("Blue", option["item_highlights"])

    def test_lower_ranked_dual_phrase_uses_retained_higher_ranked_fit_base(self):
        dual_text = "Self-Adhesive Industrial Strength Velcro Mounting System"
        report = self.report(dual_text=dual_text, move_sku=True)
        second_dual = report["title_options_generation"]["reference_phrase_analysis"][5]
        second_dual.update({
            "priority": "dual_value_differentiator",
            "keyword_refs": ["KW-FOLD"],
            "selling_point_refs": ["SP-FOLD"],
            "differentiation_refs": ["DIFF-FOLD"],
            "dual_value_rank": 2,
            "decision_value": "high",
        })
        for option in report["title_options_2026"]:
            allocation = option["reference_phrase_allocation"][5]
            allocation["reason_code"] = "character_limit"
            allocation["title_fit_evaluation"] = {
                "base_title": option["sku_fit_evaluation"]["priority_base_title"],
                "evaluated_text": "Foldable",
                "combined_characters": len(f"{option['sku_fit_evaluation']['priority_base_title']} Foldable"),
                "fits": False,
                "reason": "保留排名更高的双重差异化词后无法继续容纳该词",
            }

        result = self.validate_archived(report)
        self.assertTrue(result["ok"], result["errors"])

        broken = copy.deepcopy(report)
        for option in broken["title_options_2026"]:
            evaluation = option["reference_phrase_allocation"][5]["title_fit_evaluation"]
            evaluation["base_title"] = "FlexiCo Travel Mat"
            evaluation["combined_characters"] = len("FlexiCo Travel Mat Foldable")
            evaluation["fits"] = True
        result = self.validate_archived(broken)
        self.assertFalse(result["ok"])
        self.assertTrue(any("higher-ranked" in error for error in result["errors"]))

    def test_unfit_top_dual_phrase_moves_before_sku_is_recalculated(self):
        dual_text = (
            "Self-Adhesive Industrial Strength Reinforced Velcro Mounting System"
        )
        report = self.report(dual_text=dual_text, move_sku=True)
        identity_title = "FlexiCo Travel Mat"
        title = "FlexiCo Travel Mat, Blue, 60x40cm"
        highlights = f"{dual_text}, Foldable, storage bag"
        with_sku = "FlexiCo Travel Mat Blue 60 x 40 cm"
        for option in report["title_options_2026"]:
            option["title"] = title
            option["item_highlights"] = highlights
            option["title_components"]["differentiator"] = ""
            option["sku_attribute_placement"] = "title"
            option["sku_move_reason"] = ""
            dual_allocation = option["reference_phrase_allocation"][2]
            dual_allocation["realizations"] = [
                self.realization(
                    "item_highlights", dual_text, "verbatim", "FACT-DUAL"
                )
            ]
            dual_allocation["reason_code"] = "character_limit"
            dual_allocation["title_fit_evaluation"] = {
                "base_title": identity_title,
                "evaluated_text": dual_text,
                "combined_characters": len(f"{identity_title} {dual_text}"),
                "fits": False,
                "reason": "该词与品牌和核心品类组合后超过75字符",
            }
            option["reference_phrase_allocation"][3]["realizations"] = [
                self.realization("title", "Blue", "verbatim", "FACT-COLOR")
            ]
            option["reference_phrase_allocation"][4]["realizations"] = [
                self.realization(
                    "title", "60x40cm", "normalized", "FACT-SIZE", ["compact_unit"]
                )
            ]
            option["sku_fit_evaluation"] = {
                "priority_base_title": identity_title,
                "sku_attributes": ["Blue", "60 x 40 cm"],
                "base_characters": len(identity_title),
                "with_sku_characters": len(with_sku),
                "limit": 75,
                "fits": True,
                "final_placement": "title",
                "reason": "高优先级词因自身超限迁移后重新评估完整SKU属性组",
            }

        result = self.validate_archived(report)
        self.assertTrue(result["ok"], result["errors"])

    def test_four_case_differentiators_require_direct_fact_references(self):
        for dual_text in (
            "verstecktes",
            "Heart Shaped",
            "Kunstkaninchenfell",
            "à Ventouses",
        ):
            with self.subTest(dual_text=dual_text):
                report = self.report(dual_text=dual_text)
                result = self.validate_archived(report)
                self.assertTrue(result["ok"], result["errors"])

                unsupported = copy.deepcopy(report)
                phrase = unsupported["title_options_generation"]["reference_phrase_analysis"][2]
                phrase["fact_refs"] = []
                result = self.validate_archived(unsupported)
                self.assertFalse(result["ok"])
                self.assertTrue(any("fact_refs" in error for error in result["errors"]))

    def test_dual_phrase_that_fits_cannot_be_dropped_for_sku(self):
        report = self.report()
        for option in report["title_options_2026"]:
            option["title"] = option["title"].replace(" Waterproof", "")
            option["item_highlights"] = "Waterproof, " + option["item_highlights"]
            allocation = option["reference_phrase_allocation"][2]
            allocation["realizations"] = [
                self.realization(
                    "item_highlights", "Waterproof", "verbatim", "FACT-DUAL"
                )
            ]
            allocation["reason_code"] = "character_limit"
            allocation["title_fit_evaluation"] = {
                "base_title": "FlexiCo Travel Mat",
                "evaluated_text": "Waterproof",
                "combined_characters": len("FlexiCo Travel Mat Waterproof"),
                "fits": True,
                "reason": "测试错误地声称双重差异化词无法放入标题",
            }
            option["sku_fit_evaluation"]["priority_base_title"] = "FlexiCo Travel Mat"
            option["sku_fit_evaluation"]["base_characters"] = len("FlexiCo Travel Mat")
            option["sku_fit_evaluation"]["with_sku_characters"] = len(
                "FlexiCo Travel Mat Blue 60 x 40 cm"
            )
        result = self.validate_archived(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("cannot use character_limit" in error for error in result["errors"]))

    def test_cross_field_anchor_and_full_phrase_are_supported(self):
        report = self.report(dual_text="Self-Adhesive Velcro Base", cross_field=True)
        result = self.validate_archived(report)
        self.assertTrue(result["ok"], result["errors"])

        for option in report["title_options_2026"]:
            allocation = option["reference_phrase_allocation"][2]
            allocation["realizations"][1] = self.realization(
                "item_highlights", "Velcro", "controlled_rewrite", "FACT-DUAL", ["retain_anchor"]
            )
            option["item_highlights"] = option["item_highlights"].replace(
                "Self-Adhesive Velcro Base", "Velcro"
            )
        result = self.validate_archived(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("must add verified information" in error for error in result["errors"]))

    def test_supported_role_label_requires_fact_backed_added_tokens(self):
        errors = []
        realization = self.realization(
            "item_highlights",
            "MDF-Material",
            "supported_refinement",
            "FACT-MDF",
            ["add_role_label"],
            ["Material"],
        )
        VALIDATOR.validate_v2_realization(
            realization,
            "test",
            "MDF",
            "Brand Cabinet",
            "MDF-Material",
            errors,
        )
        self.assertEqual(errors, [])

        realization["fact_refs"] = []
        errors = []
        VALIDATOR.validate_v2_realization(
            realization,
            "test",
            "MDF",
            "Brand Cabinet",
            "MDF-Material",
            errors,
        )
        self.assertTrue(any("direct product evidence" in error for error in errors))

    def test_category_aliases_cannot_stack_in_title(self):
        report = self.report()
        analysis = report["title_options_generation"]["reference_phrase_analysis"]
        analysis[1]["semantic_group_id"] = "SG-01"
        analysis[1]["semantic_relation"] = "primary"
        analysis[6]["roles"] = ["category_synonym"]
        analysis[6]["priority"] = "secondary"
        analysis[6]["decision_factor"] = "category_synonym"
        analysis[6]["semantic_group_id"] = "SG-01"
        analysis[6]["semantic_relation"] = "synonym"
        for option in report["title_options_2026"]:
            option["title"] += ", storage bag"
            option["item_highlights"] = option["item_highlights"].replace(
                ", storage bag", ""
            )
            allocation = option["reference_phrase_allocation"][6]
            allocation["realizations"] = [
                self.realization(
                    "title", "storage bag", "normalized", "FACT-BAG", ["normalize_case"]
                )
            ]
        result = VALIDATOR.validate_report(report)
        self.assertFalse(result["ok"])
        self.assertTrue(any("multiple category aliases" in error for error in result["errors"]))

if __name__ == "__main__":
    unittest.main()
