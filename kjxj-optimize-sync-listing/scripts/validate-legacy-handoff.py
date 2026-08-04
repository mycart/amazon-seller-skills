#!/usr/bin/env python3
"""Validate the mandatory legacy-listing handoff before 2026 title generation."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path


SOURCE_SKILL = "amazon-listing-optimization"
SOURCE_SKILL_PATH = "/Users/apple/.agents/skills/amazon-listing-optimization/SKILL.md"
ADAPTER = "kjxj-optimize-sync-listing/scripts/external_adapters/listing_mode_b_adapter.py"
ADAPTER_PATH = Path(__file__).with_name("external_adapters") / "listing_mode_b_adapter.py"
LOCK_PATH = Path(__file__).parents[1] / "references" / "external-dependencies.lock.json"
INPUT_SECTIONS = (
    "asin_target",
    "marketplace_language_tone",
    "core_keywords",
    "listing_eligible_keywords",
)
FORBIDDEN_REQUEST_KEYS = {
    "original_listing", "source_retrieval", "xlsm", "category_workbook",
    "variants", "competitor_asins", "competitor_listings", "selling_points",
    "product_facts", "product_facts_and_selling_points", "ppc_campaign",
    "amazon_fees", "landed_cost", "selling_price",
}
PROVIDED_STATUSES = {"processed", "used", "partially_used", "excluded"}
REFERENCE_METHOD_V1 = "legacy_reference_phrase_allocation_v1"
REFERENCE_METHOD_V2 = "legacy_reference_phrase_allocation_v2"
REFERENCE_METHOD_V3 = "legacy_reference_phrase_allocation_v3"
REFERENCE_METHOD_V4 = "legacy_reference_phrase_allocation_v4"
REFERENCE_METHODS = {REFERENCE_METHOD_V1, REFERENCE_METHOD_V2, REFERENCE_METHOD_V3, REFERENCE_METHOD_V4}
REFERENCE_METHODS_V2_PLUS = {REFERENCE_METHOD_V2, REFERENCE_METHOD_V3, REFERENCE_METHOD_V4}
QUALITY_GENERATION_STRATEGIES = (
    "search_identity",
    "purchase_decision",
    "use_context",
)
QUALITY_SCORE_LIMITS = {
    "evidence_and_policy": 35,
    "identity_and_variant_completeness": 20,
    "pair_information_coverage": 20,
    "keyword_and_search_intent": 15,
    "natural_language_and_mobile_readability": 10,
}
PHRASE_ROLES = {
    "brand", "core_product", "material", "installation", "specification",
    "sku_attribute", "function", "benefit", "use_case", "audience", "care",
    "compatibility", "quantity", "differentiator", "intent_modifier", "shape",
    "capacity", "structure", "included_accessory", "style", "category_synonym",
    "performance", "other",
}
PHRASE_PRIORITIES_V1 = (
    "identity", "sku_attribute", "dual_value", "verified_spec_or_differentiator",
    "keyword_only", "selling_point_only", "secondary", "excluded",
)
PHRASE_PRIORITIES_V2 = (
    "identity", "dual_value_differentiator", "sku_attribute", "dual_value",
    "verified_spec_or_differentiator", "keyword_only", "selling_point_only",
    "secondary", "excluded",
)
PHRASE_EVIDENCE_STATUSES = {"verified", "unsupported"}
ALLOCATION_PLACEMENTS = {"title", "item_highlights", "omitted"}
REALIZATION_PLACEMENTS = {"title", "item_highlights"}
REUSE_TYPES = {
    "verbatim", "normalized", "controlled_rewrite", "supported_refinement", "omitted",
}
ALLOCATION_STATUSES = {"used", "omitted"}
REWRITE_OPERATIONS = {
    "normalize_case", "normalize_punctuation", "compact_unit", "inflect", "reorder",
    "retain_anchor", "drop_redundant_category", "add_role_label",
    "expand_supported_detail",
}
DECISION_FACTORS = {
    "identity", "intent_qualifier", "shape", "capacity", "dimensions", "variant",
    "material", "installation", "structure", "accessory", "function", "care",
    "audience", "style", "category_synonym", "compatibility", "performance", "other",
}
DECISION_VALUES = {"required", "high", "medium", "low"}
TITLE_PAIR_PLACEMENTS = {"title", "item_highlights", "omitted"}
HIGHLIGHT_CAPACITY_STATUSES = {"achieved", "evidence_limited"}
SEMANTIC_RELATIONS = {"primary", "synonym", "functional_alias", "refinement", "none"}
OMISSION_REASON_CODES = {
    "character_limit", "redundancy", "language_quality", "policy",
    "evidence_conflict", "unsupported",
}
PRIORITY_EXCEPTION_CODES = OMISSION_REASON_CODES - {"unsupported"}
CHINESE_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
TRAFFIC_STATUSES = {"verified_metric", "user_confirmed", "not_verified"}
TRAFFIC_METRICS = {
    "search_volume", "monthly_search_volume", "impressions", "clicks", "search_frequency",
}
SHA256_RE = re.compile(r"[0-9a-f]{64}")
INVOCATION_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{11,}")
RAW_OUTPUT_SECTION_GROUPS = (
    ("Title", ("## Title", "## 商品标题", "## 标题")),
    ("Bullet Points", ("## Bullet Points", "## 五点", "## 要点")),
    ("Description", ("## Description", "## 商品描述", "## 描述")),
    ("Backend Search Terms", ("## Backend Search Terms", "## 后台搜索词", "## 后台词")),
    ("audit", ("Audit Report", "How We Built This Listing", "审核报告", "构建说明")),
    ("keyword coverage", ("Keyword Coverage", "关键词覆盖")),
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def forbidden_request_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {
            str(key) for key in value if str(key) in FORBIDDEN_REQUEST_KEYS
        } | set().union(*(forbidden_request_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(forbidden_request_keys(item) for item in value)) if value else set()
    return set()


def validate_mode_b_request(request: object, asin: str, errors: list[str]) -> None:
    if not isinstance(request, dict):
        errors.append("Legacy request must be a JSON object.")
        return
    if str(request.get("mode", "")).upper() != "B":
        errors.append("Legacy request must invoke amazon-listing-optimization Mode B.")
    if str(request.get("asin", "")).strip().upper() != asin.upper():
        errors.append("Legacy request ASIN does not match the Listing report.")
    for field in ("marketplace", "language", "tone"):
        if not str(request.get(field, "")).strip():
            errors.append(f"Legacy request {field} is required.")
    if not isinstance(request.get("core_keywords"), list) or not request["core_keywords"]:
        errors.append("Legacy request core_keywords must be a non-empty array.")
    keywords = request.get("listing_eligible_keywords")
    if not isinstance(keywords, list) or not keywords:
        errors.append("Legacy request listing_eligible_keywords must be a non-empty array.")
    elif any(not isinstance(item, dict) or not str(item.get("keyword", "")).strip()
              or not isinstance(item.get("metrics"), dict) for item in keywords):
        errors.append("Legacy request listing_eligible_keywords must retain keyword text and metrics.")
    prohibited = sorted(forbidden_request_keys(request))
    if prohibited:
        errors.append("Legacy request contains prohibited upstream inputs: " + ", ".join(prohibited))


def validate_invocation_evidence(
    legacy: dict, artifact: object | None, legacy_listing: dict, asin: str, errors: list[str]
) -> None:
    evidence_fields = (
        "source_skill_sha256",
        "request_path",
        "request_sha256",
        "raw_output_path",
        "raw_output_sha256",
    )
    provenance = legacy.get("execution_provenance") if isinstance(legacy.get("execution_provenance"), dict) else None
    invocation_id = str((provenance or {}).get("adapter_invocation_id") or legacy.get("invocation_id", "")).strip()
    if not INVOCATION_ID_RE.fullmatch(invocation_id):
        errors.append("legacy_generation.invocation_id is required and must be a stable execution ID.")
    started_at = parse_datetime(
        legacy.get("started_at"), "legacy_generation.started_at", errors
    )
    completed_at = parse_datetime(
        legacy.get("completed_at"), "legacy_generation.completed_at", errors
    )
    if started_at and completed_at:
        try:
            if completed_at < started_at:
                errors.append("legacy_generation.completed_at must not precede started_at.")
        except TypeError:
            errors.append("Legacy invocation timestamps must use compatible timezone formats.")
    for field in evidence_fields:
        value = str(legacy.get(field, "")).strip()
        if not value:
            errors.append(f"legacy_generation.{field} is required.")
        elif field.endswith("sha256") and not SHA256_RE.fullmatch(value):
            errors.append(f"legacy_generation.{field} must be a lowercase SHA-256 value.")

    if provenance is not None:
        if provenance.get("adapter") != ADAPTER:
            errors.append("execution_provenance.adapter is invalid.")
        elif not ADAPTER_PATH.is_file() or provenance.get("adapter_sha256") != file_sha256(ADAPTER_PATH):
            errors.append("execution_provenance.adapter_sha256 does not match the KJXJ adapter.")
        upstream = provenance.get("upstream_skill") if isinstance(provenance.get("upstream_skill"), dict) else {}
        if upstream.get("name") != SOURCE_SKILL or upstream.get("path") != SOURCE_SKILL_PATH:
            errors.append("execution_provenance.upstream_skill is invalid.")
        if not LOCK_PATH.is_file() or upstream.get("lock_sha256") != file_sha256(LOCK_PATH):
            errors.append("execution_provenance.upstream_skill.lock_sha256 is invalid.")
        raw = provenance.get("external_raw_output") if isinstance(provenance.get("external_raw_output"), dict) else {}
        if raw.get("path") != legacy.get("raw_output_path") or raw.get("sha256") != legacy.get("raw_output_sha256"):
            errors.append("execution_provenance.external_raw_output is not bound to legacy output.")

    if artifact is None or not isinstance(artifact, dict):
        return

    for field in evidence_fields:
        if artifact.get(field) != legacy.get(field):
            errors.append(f"Legacy artifact {field} does not match legacy_generation.")
    for field in ("started_at",):
        if artifact.get(field) != legacy.get(field):
            errors.append(f"Legacy artifact {field} does not match legacy_generation.")

    skill_path = Path(SOURCE_SKILL_PATH)
    if not skill_path.is_file():
        errors.append(f"Source skill file does not exist: {skill_path}")
    elif legacy.get("source_skill_sha256") != file_sha256(skill_path):
        errors.append("legacy_generation.source_skill_sha256 does not match the invoked skill.")

    request_path = Path(str(legacy.get("request_path", ""))).expanduser()
    if request_path.name != f"legacy-listing-request-{asin}.json":
        errors.append(f"Legacy request artifact filename must be legacy-listing-request-{asin}.json.")
    if not request_path.is_file():
        errors.append(f"Legacy request artifact does not exist: {request_path}")
    else:
        if legacy.get("request_sha256") != file_sha256(request_path):
            errors.append("legacy_generation.request_sha256 does not match the request artifact.")
        try:
            request = json.loads(request_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            errors.append("Legacy request artifact must be valid UTF-8 JSON.")
        else:
            if request.get("source_skill") != SOURCE_SKILL:
                errors.append("Legacy request source_skill is invalid.")
            if request.get("source_skill_path") != SOURCE_SKILL_PATH:
                errors.append("Legacy request source_skill_path is invalid.")
            if str(request.get("mode", "")).upper() != str(legacy.get("mode", "")).upper():
                errors.append("Legacy request mode does not match legacy_generation.mode.")
            validate_mode_b_request(request, asin, errors)
            if provenance is None and request.get("invocation_id") != invocation_id:
                errors.append("Legacy request invocation_id does not match legacy_generation.")
            # Adapter provenance records the sealing/materialization interval.  A request
            # may legitimately predate that interval, so preserve the old equality rule
            # only for pre-adapter artifacts.
            if provenance is None and request.get("created_at") != legacy.get("started_at"):
                errors.append("Legacy request created_at does not match legacy_generation.started_at.")
            if request.get("input_manifest") != legacy.get("input_manifest"):
                errors.append("Legacy request input_manifest does not match legacy_generation.")

    raw_output_path = Path(str(legacy.get("raw_output_path", ""))).expanduser()
    if raw_output_path.name != f"legacy-listing-raw-output-{asin}.md":
        errors.append(
            f"Legacy raw output filename must be legacy-listing-raw-output-{asin}.md."
        )
    if not raw_output_path.is_file():
        errors.append(f"Legacy raw output artifact does not exist: {raw_output_path}")
    else:
        if legacy.get("raw_output_sha256") != file_sha256(raw_output_path):
            errors.append("legacy_generation.raw_output_sha256 does not match the raw output artifact.")
        try:
            raw_output = raw_output_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            errors.append("Legacy raw output artifact must be readable UTF-8 Markdown.")
        else:
            required_values = [
                legacy_listing.get("title", ""),
                *(legacy_listing.get("bullets") or []),
                legacy_listing.get("description", ""),
                legacy_listing.get("backend_search_terms", ""),
            ]
            missing_values = [
                str(value) for value in required_values
                if str(value).strip() and str(value).strip() not in raw_output
            ]
            if missing_values:
                errors.append(
                    "Legacy raw output does not contain the exact structured Listing fields: "
                    + "; ".join(missing_values)
                )
            missing_sections = [
                label for label, markers in RAW_OUTPUT_SECTION_GROUPS
                if not any(marker in raw_output for marker in markers)
            ]
            if missing_sections:
                errors.append(
                    "Legacy raw output is missing required Listing or audit sections: "
                    + ", ".join(missing_sections)
                    + "."
                )


def load_title_validator():
    script = Path(__file__).with_name("validate-title-highlights.py")
    spec = importlib.util.spec_from_file_location("title_highlights_validator", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


TITLE_VALIDATOR = load_title_validator()
FUNCTION_WORDS = TITLE_VALIDATOR.STOPWORDS | {
    "aus", "zum", "zur", "bei", "auf", "am", "by", "from", "as",
    "sur", "par", "du", "au", "aux", "da", "do", "em", "na", "no",
    "en", "por", "del", "al", "zu",
}


def parse_datetime(value: object, label: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required.")
        return None
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} must be an ISO 8601 timestamp.")
        return None


def validate_listing(listing: object, errors: list[str]) -> dict:
    if not isinstance(listing, dict):
        errors.append("legacy_listing must be an object.")
        return {}

    title = str(listing.get("title", "")).strip()
    if not title:
        errors.append("legacy_listing.title is required.")
    elif len(title) > 200:
        errors.append(f"legacy_listing.title has {len(title)} characters; limit is 200.")

    bullets = listing.get("bullets")
    if not isinstance(bullets, list) or len(bullets) != 5:
        errors.append("legacy_listing.bullets must contain exactly 5 items.")
    else:
        for index, bullet in enumerate(bullets, start=1):
            value = str(bullet).strip()
            if not value:
                errors.append(f"legacy_listing.bullets[{index}] is empty.")
            elif len(value) > 500:
                errors.append(
                    f"legacy_listing.bullets[{index}] has {len(value)} characters; limit is 500."
                )

    description = str(listing.get("description", "")).strip()
    if not description:
        errors.append("legacy_listing.description is required.")
    elif len(description) > 2000:
        errors.append(
            f"legacy_listing.description has {len(description)} characters; limit is 2000."
        )

    if not str(listing.get("backend_search_terms", "")).strip():
        errors.append("legacy_listing.backend_search_terms is required.")
    return listing


def validate_manifest(manifest: object, errors: list[str]) -> dict:
    if not isinstance(manifest, dict):
        errors.append("legacy_generation.input_manifest must be an object.")
        return {}

    for section in INPUT_SECTIONS:
        entry = manifest.get(section)
        if not isinstance(entry, dict):
            errors.append(f"input_manifest.{section} is required.")
            continue
        provided = entry.get("provided")
        status = str(entry.get("status", "")).strip()
        note = str(entry.get("note", "")).strip()
        if not isinstance(provided, bool):
            errors.append(f"input_manifest.{section}.provided must be boolean.")
        elif provided and status not in PROVIDED_STATUSES:
            errors.append(
                f"input_manifest.{section}.status must record how the provided input was processed."
            )
        elif provided and "data" not in entry:
            errors.append(f"input_manifest.{section}.data is required for provided input.")
        elif not provided and status != "not_provided":
            errors.append(f"input_manifest.{section}.status must be not_provided.")
        if not note:
            errors.append(f"input_manifest.{section}.note is required.")
    return manifest


def normalized_text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split()).casefold()


def evidence_tokens(value: object) -> Counter[str]:
    return Counter(
        token for token in TITLE_VALIDATOR.words(str(value or ""))
        if token not in FUNCTION_WORDS
    )


def controlled_rewrite_is_supported(source_text: str, realization: str) -> bool:
    """Allow omission, inflection, and compact units, but no unrelated content words."""
    source_tokens = list(evidence_tokens(source_text))
    realization_tokens = list(evidence_tokens(realization))
    for token in realization_tokens:
        if token in source_tokens:
            continue
        if any(
            min(len(token), len(source_token)) >= 5
            and (token.startswith(source_token) or source_token.startswith(token))
            for source_token in source_tokens
        ):
            continue
        return False
    return True


def token_is_related(left: str, right: str) -> bool:
    if left == right:
        return True
    return min(len(left), len(right)) >= 5 and (
        left.startswith(right) or right.startswith(left)
    )


def added_content_tokens(source_text: str, realization: str) -> Counter[str]:
    source = list(evidence_tokens(source_text).elements())
    added: Counter[str] = Counter()
    for token in evidence_tokens(realization).elements():
        matched_index = next(
            (index for index, source_token in enumerate(source) if token_is_related(token, source_token)),
            None,
        )
        if matched_index is None:
            added[token] += 1
        else:
            source.pop(matched_index)
    return added


def has_information_increment(summary: str, detail: str) -> bool:
    summary_tokens = list(evidence_tokens(summary).elements())
    for token in evidence_tokens(detail).elements():
        matched_index = next(
            (index for index, existing in enumerate(summary_tokens) if token_is_related(token, existing)),
            None,
        )
        if matched_index is None:
            return True
        summary_tokens.pop(matched_index)
    return False


def string_list(value: object, label: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array.")
        return []
    result = [str(item).strip() for item in value]
    if any(not item for item in result):
        errors.append(f"{label} must not contain empty values.")
    if len(set(result)) != len(result):
        errors.append(f"{label} must not contain duplicate values.")
    return result


def expected_priority(phrase: dict, roles: set[str], method: str = REFERENCE_METHOD_V1) -> str:
    keyword_refs = phrase.get("keyword_refs") or []
    selling_point_refs = phrase.get("selling_point_refs") or []
    differentiation_refs = phrase.get("differentiation_refs") or []
    if roles.intersection({"brand", "core_product"}):
        return "identity"
    if (
        method in REFERENCE_METHODS_V2_PLUS
        and keyword_refs
        and selling_point_refs
        and differentiation_refs
        and phrase.get("fact_refs")
    ):
        return "dual_value_differentiator"
    if "sku_attribute" in roles:
        return "sku_attribute"
    if keyword_refs and selling_point_refs:
        return "dual_value"
    if roles.intersection({
        "material", "installation", "specification", "compatibility", "quantity",
        "differentiator", "intent_modifier", "shape", "capacity", "structure",
        "included_accessory", "performance",
    }):
        return "verified_spec_or_differentiator"
    if keyword_refs:
        return "keyword_only"
    if selling_point_refs:
        return "selling_point_only"
    return "secondary"


def validate_reference_phrase_analysis(
    generation: dict, legacy_title: str, errors: list[str], method: str = REFERENCE_METHOD_V1
) -> dict[str, dict]:
    phrases = generation.get("reference_phrase_analysis")
    if not isinstance(phrases, list) or not phrases:
        errors.append("title_options_generation.reference_phrase_analysis must be a non-empty array.")
        return {}

    by_id: dict[str, dict] = {}
    source_tokens: Counter[str] = Counter()
    reference_text = unicodedata.normalize("NFKC", legacy_title).casefold()
    source_cursor = 0
    dual_value_ranks: list[int] = []
    priorities = PHRASE_PRIORITIES_V2 if method in REFERENCE_METHODS_V2_PLUS else PHRASE_PRIORITIES_V1
    for index, phrase in enumerate(phrases, start=1):
        label = f"reference_phrase_analysis[{index}]"
        if not isinstance(phrase, dict):
            errors.append(f"{label} must be an object.")
            continue
        phrase_id = str(phrase.get("id", "")).strip()
        if not re.fullmatch(r"RP-\d{2,}", phrase_id):
            errors.append(f"{label}.id must match RP- followed by at least two digits.")
        elif phrase_id in by_id:
            errors.append(f"{label}.id is duplicated: {phrase_id}")
        else:
            by_id[phrase_id] = phrase

        source_text = str(phrase.get("source_text", "")).strip()
        if not source_text:
            errors.append(f"{label}.source_text is required.")
        else:
            source_fragment = unicodedata.normalize("NFKC", source_text).casefold()
            source_position = reference_text.find(source_fragment, source_cursor)
            if source_position < 0:
                errors.append(
                    f"{label}.source_text must be exact reference-title text in source order."
                )
            else:
                source_cursor = source_position + len(source_fragment)
        source_tokens.update(evidence_tokens(source_text))
        normalized_phrase = str(phrase.get("normalized_text", "")).strip()
        if not normalized_phrase:
            errors.append(f"{label}.normalized_text is required.")
        elif normalized_text(normalized_phrase) != normalized_text(source_text):
            errors.append(f"{label}.normalized_text must be the normalized source_text.")
        if phrase.get("source_order") != index:
            errors.append(f"{label}.source_order must preserve the 1-based reference-title order.")

        roles_value = phrase.get("roles")
        roles = set(string_list(roles_value, f"{label}.roles", errors))
        if not roles:
            errors.append(f"{label}.roles must not be empty.")
        invalid_roles = sorted(roles - PHRASE_ROLES)
        if invalid_roles:
            errors.append(f"{label}.roles contains unsupported values: {', '.join(invalid_roles)}")
        keyword_refs = string_list(phrase.get("keyword_refs"), f"{label}.keyword_refs", errors)
        selling_refs = string_list(
            phrase.get("selling_point_refs"), f"{label}.selling_point_refs", errors
        )
        fact_refs = string_list(phrase.get("fact_refs"), f"{label}.fact_refs", errors)
        differentiation_refs: list[str] = []
        if method in REFERENCE_METHODS_V2_PLUS:
            differentiation_refs = string_list(
                phrase.get("differentiation_refs"), f"{label}.differentiation_refs", errors
            )

            decision_factor = str(phrase.get("decision_factor", "")).strip()
            if decision_factor not in DECISION_FACTORS:
                errors.append(f"{label}.decision_factor is invalid.")
            decision_value = str(phrase.get("decision_value", "")).strip()
            if decision_value not in DECISION_VALUES:
                errors.append(f"{label}.decision_value is invalid.")
            decision_reason = str(phrase.get("decision_reason", "")).strip()
            if not decision_reason or not CHINESE_RE.search(decision_reason):
                errors.append(f"{label}.decision_reason must be a non-empty Chinese explanation.")

            semantic_group_id = str(phrase.get("semantic_group_id", "")).strip()
            semantic_relation = str(phrase.get("semantic_relation", "")).strip()
            if semantic_relation not in SEMANTIC_RELATIONS:
                errors.append(f"{label}.semantic_relation is invalid.")
            elif semantic_relation == "none" and semantic_group_id:
                errors.append(f"{label}.semantic_group_id must be empty when relation is none.")
            elif semantic_relation != "none" and not re.fullmatch(r"SG-\d{2,}", semantic_group_id):
                errors.append(
                    f"{label}.semantic_group_id must match SG- followed by at least two digits."
                )
        evidence_status = str(phrase.get("evidence_status", "")).strip()
        if evidence_status not in PHRASE_EVIDENCE_STATUSES:
            errors.append(f"{label}.evidence_status is invalid.")
        if evidence_status == "verified" and not fact_refs:
            errors.append(f"{label}.fact_refs is required for verified phrases.")
        priority = str(phrase.get("priority", "")).strip()
        if priority not in priorities:
            errors.append(f"{label}.priority is invalid.")
        elif evidence_status == "unsupported":
            if priority != "excluded":
                errors.append(f"{label}.priority must be excluded when evidence is unsupported.")
        else:
            calculated = expected_priority(
                {
                    **phrase,
                    "keyword_refs": keyword_refs,
                    "selling_point_refs": selling_refs,
                    "differentiation_refs": differentiation_refs,
                    "fact_refs": fact_refs,
                },
                roles,
                method,
            )
            if priority != calculated:
                errors.append(f"{label}.priority must be {calculated} for its roles and references.")

        if method in REFERENCE_METHODS_V2_PLUS:
            dual_value_rank = phrase.get("dual_value_rank", 0)
            if priority == "dual_value_differentiator":
                if not isinstance(dual_value_rank, int) or dual_value_rank <= 0:
                    errors.append(
                        f"{label}.dual_value_rank must be a positive integer for "
                        "dual_value_differentiator phrases."
                    )
                else:
                    dual_value_ranks.append(dual_value_rank)
            elif dual_value_rank not in (0, None):
                errors.append(
                    f"{label}.dual_value_rank must be 0 for non-dual-value-differentiator phrases."
                )

    if source_tokens != evidence_tokens(legacy_title):
        errors.append(
            "reference_phrase_analysis must completely decompose legacy_listing.title without "
            "dropping or duplicating evidence-bearing tokens."
        )
    if method in REFERENCE_METHODS_V2_PLUS and dual_value_ranks:
        expected_ranks = list(range(1, len(dual_value_ranks) + 1))
        if sorted(dual_value_ranks) != expected_ranks:
            errors.append(
                "dual_value_differentiator dual_value_rank values must be unique and contiguous "
                "starting at 1."
            )
    return by_id


def validate_additional_phrases(
    option: dict, option_label: str, title: str, highlights: str, errors: list[str]
) -> Counter[str]:
    additions = option.get("additional_verified_phrases", [])
    if not isinstance(additions, list):
        errors.append(f"{option_label}.additional_verified_phrases must be an array.")
        return Counter()
    tokens: Counter[str] = Counter()
    for index, item in enumerate(additions, start=1):
        label = f"{option_label}.additional_verified_phrases[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{label} must be an object.")
            continue
        text = str(item.get("text", "")).strip()
        placement = str(item.get("placement", "")).strip()
        if not text:
            errors.append(f"{label}.text is required.")
        if placement not in {"title", "item_highlights"}:
            errors.append(f"{label}.placement must be title or item_highlights.")
        elif text and not TITLE_VALIDATOR.contains_component(
            title if placement == "title" else highlights, text
        ):
            errors.append(f"{label}.text is not present in its declared field.")
        if not string_list(item.get("fact_refs"), f"{label}.fact_refs", errors):
            errors.append(f"{label}.fact_refs must contain direct product evidence.")
        string_list(item.get("keyword_refs", []), f"{label}.keyword_refs", errors)
        string_list(item.get("selling_point_refs", []), f"{label}.selling_point_refs", errors)
        reason = str(item.get("reason", "")).strip()
        if not reason or not CHINESE_RE.search(reason):
            errors.append(f"{label}.reason must be a non-empty Chinese explanation.")
        tokens.update(evidence_tokens(text))
    return tokens


def validate_phrase_allocation(
    option: dict,
    option_index: int,
    phrases: dict[str, dict],
    errors: list[str],
) -> None:
    option_label = f"title_options_2026[{option_index}]"
    allocations = option.get("reference_phrase_allocation")
    if not isinstance(allocations, list):
        errors.append(f"{option_label}.reference_phrase_allocation must be an array.")
        return
    if len(allocations) != len(phrases):
        errors.append(f"{option_label}.reference_phrase_allocation must cover every reference phrase.")

    title = str(option.get("title", ""))
    highlights = str(option.get("item_highlights", ""))
    seen: set[str] = set()
    realized_tokens: Counter[str] = Counter()
    included_priorities: list[int] = []
    omitted: list[tuple[str, int, str]] = []
    priority_rank = {value: index for index, value in enumerate(PHRASE_PRIORITIES_V1)}

    for allocation_index, allocation in enumerate(allocations, start=1):
        label = f"{option_label}.reference_phrase_allocation[{allocation_index}]"
        if not isinstance(allocation, dict):
            errors.append(f"{label} must be an object.")
            continue
        phrase_id = str(allocation.get("phrase_id", "")).strip()
        if phrase_id not in phrases:
            errors.append(f"{label}.phrase_id does not reference reference_phrase_analysis.")
            continue
        if phrase_id in seen:
            errors.append(f"{label}.phrase_id is duplicated: {phrase_id}")
            continue
        seen.add(phrase_id)
        phrase = phrases[phrase_id]
        placement = str(allocation.get("placement", "")).strip()
        reuse_type = str(allocation.get("reuse_type", "")).strip()
        realization = str(allocation.get("realization", "")).strip()
        reason = str(allocation.get("reason", "")).strip()
        reason_code = str(allocation.get("reason_code", "")).strip()
        if placement not in ALLOCATION_PLACEMENTS:
            errors.append(f"{label}.placement is invalid.")
        if reuse_type not in REUSE_TYPES:
            errors.append(f"{label}.reuse_type is invalid.")
        if not reason or not CHINESE_RE.search(reason):
            errors.append(f"{label}.reason must be a non-empty Chinese explanation.")

        evidence_status = str(phrase.get("evidence_status", ""))
        rank = priority_rank.get(str(phrase.get("priority", "")), len(priority_rank))
        if placement == "omitted":
            if reuse_type != "omitted" or realization:
                errors.append(f"{label} omitted phrases require reuse_type omitted and empty realization.")
            if reason_code not in OMISSION_REASON_CODES:
                errors.append(f"{label}.reason_code is invalid for an omitted phrase.")
            if evidence_status == "verified" and reason_code == "unsupported":
                errors.append(f"{label}.reason_code unsupported is reserved for unsupported evidence.")
            omitted.append((label, rank, reason_code))
            continue

        if reason_code not in {"retained", *PRIORITY_EXCEPTION_CODES}:
            errors.append(f"{label}.reason_code is invalid for a used phrase.")
        if reuse_type == "omitted" or not realization:
            errors.append(f"{label} used phrases require a realization and non-omitted reuse_type.")
            continue
        if evidence_status != "verified" or not phrase.get("fact_refs"):
            errors.append(f"{label} cannot use a phrase without direct verified fact evidence.")
        field_value = title if placement == "title" else highlights
        if not TITLE_VALIDATOR.contains_component(field_value, realization):
            errors.append(f"{label}.realization is not present in its declared field.")
        source_text = str(phrase.get("source_text", "")).strip()
        if reuse_type == "verbatim" and realization != source_text:
            errors.append(f"{label} verbatim realization must exactly equal source_text.")
        if reuse_type == "normalized" and evidence_tokens(realization) != evidence_tokens(source_text):
            errors.append(f"{label} normalized realization must preserve source tokens.")
        if reuse_type == "controlled_rewrite" and not controlled_rewrite_is_supported(
            source_text, realization
        ):
            errors.append(
                f"{label} controlled_rewrite introduces content not derived from source_text; "
                "declare it in additional_verified_phrases instead."
            )
        included_priorities.append(rank)
        realized_tokens.update(evidence_tokens(realization))

    missing_ids = sorted(set(phrases) - seen)
    if missing_ids:
        errors.append(f"{option_label} is missing phrase allocations: {', '.join(missing_ids)}")

    if included_priorities:
        lowest_included_priority = max(included_priorities)
        for label, omitted_rank, reason_code in omitted:
            if omitted_rank < lowest_included_priority and reason_code not in PRIORITY_EXCEPTION_CODES:
                errors.append(
                    f"{label} omits a higher-priority phrase while retaining lower-priority content "
                    "without an allowed exception."
                )

    realized_tokens.update(
        validate_additional_phrases(option, option_label, title, highlights, errors)
    )
    candidate_tokens = evidence_tokens(f"{title} {highlights}")
    if realized_tokens != candidate_tokens:
        errors.append(
            f"{option_label} contains content tokens not covered exactly by reference phrase "
            "allocations or additional_verified_phrases."
        )


def validate_v2_realization(
    realization: object,
    label: str,
    source_text: str,
    title: str,
    highlights: str,
    errors: list[str],
) -> tuple[str, str, Counter[str]]:
    if not isinstance(realization, dict):
        errors.append(f"{label} must be an object.")
        return "", "", Counter()

    placement = str(realization.get("placement", "")).strip()
    text = str(realization.get("text", "")).strip()
    reuse_type = str(realization.get("reuse_type", "")).strip()
    if placement not in REALIZATION_PLACEMENTS:
        errors.append(f"{label}.placement is invalid.")
    if not text:
        errors.append(f"{label}.text is required.")
    elif placement in REALIZATION_PLACEMENTS and not TITLE_VALIDATOR.contains_component(
        title if placement == "title" else highlights, text
    ):
        errors.append(f"{label}.text is not present in its declared field.")
    if reuse_type not in REUSE_TYPES - {"omitted"}:
        errors.append(f"{label}.reuse_type is invalid.")

    operations = string_list(
        realization.get("rewrite_operations"), f"{label}.rewrite_operations", errors
    )
    invalid_operations = sorted(set(operations) - REWRITE_OPERATIONS)
    if invalid_operations:
        errors.append(
            f"{label}.rewrite_operations contains unsupported values: "
            + ", ".join(invalid_operations)
        )
    added_tokens = string_list(
        realization.get("added_tokens"), f"{label}.added_tokens", errors
    )
    fact_refs = string_list(realization.get("fact_refs"), f"{label}.fact_refs", errors)
    if not fact_refs:
        errors.append(f"{label}.fact_refs must contain direct product evidence.")
    reason = str(realization.get("reason", "")).strip()
    if not reason or not CHINESE_RE.search(reason):
        errors.append(f"{label}.reason must be a non-empty Chinese explanation.")

    if reuse_type == "verbatim":
        if text != source_text:
            errors.append(f"{label} verbatim text must exactly equal source_text.")
        if operations or added_tokens:
            errors.append(f"{label} verbatim text must not declare rewrites or added tokens.")
    elif reuse_type == "normalized":
        if evidence_tokens(text) != evidence_tokens(source_text):
            errors.append(f"{label} normalized text must preserve source tokens.")
        if added_tokens:
            errors.append(f"{label} normalized text must not declare added tokens.")
    elif reuse_type == "controlled_rewrite":
        if not controlled_rewrite_is_supported(source_text, text):
            errors.append(
                f"{label} controlled_rewrite introduces unrelated content; use "
                "supported_refinement or additional_verified_phrases."
            )
        if added_tokens:
            errors.append(f"{label} controlled_rewrite must not declare added tokens.")
        if not operations:
            errors.append(f"{label} controlled_rewrite requires rewrite_operations.")
    elif reuse_type == "supported_refinement":
        calculated_added = added_content_tokens(source_text, text)
        declared_added = evidence_tokens(" ".join(added_tokens))
        if not calculated_added or calculated_added != declared_added:
            errors.append(
                f"{label} supported_refinement added_tokens must exactly cover new content tokens."
            )
        if not set(operations).intersection({"add_role_label", "expand_supported_detail"}):
            errors.append(
                f"{label} supported_refinement requires add_role_label or "
                "expand_supported_detail."
            )

    return placement, text, evidence_tokens(text)


def validate_title_fit_evaluation(
    allocation: dict,
    label: str,
    components: dict,
    source_text: str,
    higher_ranked_title_realizations: list[str],
    reason_code: str,
    errors: list[str],
) -> None:
    evaluation = allocation.get("title_fit_evaluation")
    if not isinstance(evaluation, dict):
        errors.append(f"{label}.title_fit_evaluation is required when the phrase is not in Title.")
        return
    base_title = str(evaluation.get("base_title", "")).strip()
    evaluated_text = str(evaluation.get("evaluated_text", "")).strip()
    if not base_title or not evaluated_text:
        errors.append(f"{label}.title_fit_evaluation requires base_title and evaluated_text.")
        return
    for component_name in ("brand", "core_product_phrase"):
        component = str(components.get(component_name, "")).strip()
        if component and not TITLE_VALIDATOR.contains_component(base_title, component):
            errors.append(
                f"{label}.title_fit_evaluation.base_title is missing {component_name}."
            )
    for realization in higher_ranked_title_realizations:
        if not TITLE_VALIDATOR.contains_component(base_title, realization):
            errors.append(
                f"{label}.title_fit_evaluation.base_title must retain higher-ranked "
                f"dual-value differentiator: {realization}"
            )
    sku_attributes = components.get("sku_attributes") or []
    for attribute in sku_attributes:
        if TITLE_VALIDATOR.contains_sku_attribute(base_title, str(attribute)):
            errors.append(
                f"{label}.title_fit_evaluation.base_title must evaluate the phrase before SKU "
                f"attributes: {attribute}"
            )
    expected_base_parts = [
        str(components.get("brand", "")).strip(),
        str(components.get("core_product_phrase", "")).strip(),
        *higher_ranked_title_realizations,
    ]
    expected_base_tokens = evidence_tokens(
        " ".join(part for part in expected_base_parts if part)
    )
    if evidence_tokens(base_title) != expected_base_tokens:
        errors.append(
            f"{label}.title_fit_evaluation.base_title must contain only brand, core product, "
            "and retained higher-ranked dual-value differentiators."
        )
    if not controlled_rewrite_is_supported(source_text, evaluated_text):
        errors.append(
            f"{label}.title_fit_evaluation.evaluated_text must be a controlled rewrite of "
            "the reference phrase."
        )
    combined_title = " ".join([base_title.rstrip(" ,;，；"), evaluated_text])
    combined_characters = len(TITLE_VALIDATOR.normalize(combined_title))
    if evaluation.get("combined_characters") != combined_characters:
        errors.append(f"{label}.title_fit_evaluation.combined_characters is incorrect.")
    fits = evaluation.get("fits")
    if not isinstance(fits, bool) or fits != (combined_characters <= TITLE_VALIDATOR.TITLE_LIMIT):
        errors.append(f"{label}.title_fit_evaluation.fits is inconsistent with the character limit.")
    reason = str(evaluation.get("reason", "")).strip()
    if not reason or not CHINESE_RE.search(reason):
        errors.append(f"{label}.title_fit_evaluation.reason must be a Chinese explanation.")
    if fits and reason_code == "character_limit":
        errors.append(
            f"{label} cannot use character_limit because its evaluated realization fits in Title."
        )


def validate_sku_fit_evaluation(
    option: dict,
    option_label: str,
    components: dict,
    dual_title_realizations: list[str],
    errors: list[str],
) -> str:
    evaluation = option.get("sku_fit_evaluation")
    if not isinstance(evaluation, dict):
        errors.append(f"{option_label}.sku_fit_evaluation is required for semantic allocation options.")
        return ""

    base_title = str(evaluation.get("priority_base_title", "")).strip()
    sku_attributes = components.get("sku_attributes") or []
    evaluated_sku = evaluation.get("sku_attributes")
    if evaluated_sku != sku_attributes:
        errors.append(f"{option_label}.sku_fit_evaluation.sku_attributes must match title_components.")
    for component_name in ("brand", "core_product_phrase"):
        component = str(components.get(component_name, "")).strip()
        if component and not TITLE_VALIDATOR.contains_component(base_title, component):
            errors.append(
                f"{option_label}.sku_fit_evaluation.priority_base_title is missing "
                f"{component_name}."
            )
    for realization in dual_title_realizations:
        if not TITLE_VALIDATOR.contains_component(base_title, realization):
            errors.append(
                f"{option_label}.sku_fit_evaluation.priority_base_title must retain higher-priority "
                f"dual-value differentiator: {realization}"
            )
    for attribute in sku_attributes:
        if TITLE_VALIDATOR.contains_sku_attribute(base_title, str(attribute)):
            errors.append(
                f"{option_label}.sku_fit_evaluation.priority_base_title must exclude SKU attribute: "
                f"{attribute}"
            )

    normalized_base = TITLE_VALIDATOR.normalize(base_title)
    with_sku = " ".join([normalized_base.rstrip(" ,;，；"), *map(str, sku_attributes)]).strip()
    base_characters = len(normalized_base)
    with_sku_characters = len(with_sku)
    if evaluation.get("base_characters") != base_characters:
        errors.append(f"{option_label}.sku_fit_evaluation.base_characters is incorrect.")
    if evaluation.get("with_sku_characters") != with_sku_characters:
        errors.append(f"{option_label}.sku_fit_evaluation.with_sku_characters is incorrect.")
    if evaluation.get("limit") != TITLE_VALIDATOR.TITLE_LIMIT:
        errors.append(f"{option_label}.sku_fit_evaluation.limit must be 75.")
    fits = evaluation.get("fits")
    expected_fits = not sku_attributes or with_sku_characters <= TITLE_VALIDATOR.TITLE_LIMIT
    if not isinstance(fits, bool) or fits != expected_fits:
        errors.append(f"{option_label}.sku_fit_evaluation.fits is inconsistent with its character count.")

    final_placement = str(evaluation.get("final_placement", "")).strip()
    option_placement = str(option.get("sku_attribute_placement", "")).strip()
    if final_placement != option_placement:
        errors.append(f"{option_label}.sku_fit_evaluation.final_placement must match the option.")
    if not sku_attributes and final_placement != "not_applicable":
        errors.append(f"{option_label}.sku_fit_evaluation must use not_applicable without SKU data.")
    elif sku_attributes and expected_fits and final_placement != "title":
        errors.append(
            f"{option_label} SKU attributes fit after higher-priority phrases and must remain in Title."
        )
    elif sku_attributes and not expected_fits and final_placement != "item_highlights":
        errors.append(
            f"{option_label} SKU attributes exceed 75 characters after higher-priority phrases "
            "and must move to Item Highlights."
        )
    sku_move_reason = str(option.get("sku_move_reason", "")).strip()
    if final_placement == "item_highlights":
        if not sku_move_reason or not CHINESE_RE.search(sku_move_reason):
            errors.append(f"{option_label}.sku_move_reason must explain the move in Chinese.")
    elif sku_move_reason:
        errors.append(f"{option_label}.sku_move_reason is only allowed when SKU moves to highlights.")
    reason = str(evaluation.get("reason", "")).strip()
    if not reason or not CHINESE_RE.search(reason):
        errors.append(f"{option_label}.sku_fit_evaluation.reason must be a Chinese explanation.")
    return base_title


def validate_phrase_allocation_v2(
    option: dict,
    option_index: int,
    phrases: dict[str, dict],
    components: dict,
    errors: list[str],
) -> str:
    option_label = f"title_options_2026[{option_index}]"
    allocations = option.get("reference_phrase_allocation")
    if not isinstance(allocations, list):
        errors.append(f"{option_label}.reference_phrase_allocation must be an array.")
        return ""
    if len(allocations) != len(phrases):
        errors.append(f"{option_label}.reference_phrase_allocation must cover every reference phrase.")

    title = str(option.get("title", ""))
    highlights = str(option.get("item_highlights", ""))
    seen: set[str] = set()
    realized_tokens: Counter[str] = Counter()
    allocation_by_phrase: dict[str, dict] = {}
    title_realizations_by_phrase: dict[str, list[str]] = {}
    title_semantic_groups: dict[str, list[str]] = {}
    priorities = {value: index for index, value in enumerate(PHRASE_PRIORITIES_V2)}
    title_priorities: list[tuple[str, int]] = []

    for allocation_index, allocation in enumerate(allocations, start=1):
        label = f"{option_label}.reference_phrase_allocation[{allocation_index}]"
        if not isinstance(allocation, dict):
            errors.append(f"{label} must be an object.")
            continue
        phrase_id = str(allocation.get("phrase_id", "")).strip()
        if phrase_id not in phrases:
            errors.append(f"{label}.phrase_id does not reference reference_phrase_analysis.")
            continue
        if phrase_id in seen:
            errors.append(f"{label}.phrase_id is duplicated: {phrase_id}")
            continue
        seen.add(phrase_id)
        allocation_by_phrase[phrase_id] = allocation
        phrase = phrases[phrase_id]
        status = str(allocation.get("status", "")).strip()
        reason_code = str(allocation.get("reason_code", "")).strip()
        reason = str(allocation.get("reason", "")).strip()
        if status not in ALLOCATION_STATUSES:
            errors.append(f"{label}.status is invalid.")
        if not reason or not CHINESE_RE.search(reason):
            errors.append(f"{label}.reason must be a non-empty Chinese explanation.")
        realizations = allocation.get("realizations")
        if not isinstance(realizations, list):
            errors.append(f"{label}.realizations must be an array.")
            realizations = []

        if status == "omitted":
            if realizations:
                errors.append(f"{label} omitted phrases must not contain realizations.")
            if reason_code not in OMISSION_REASON_CODES:
                errors.append(f"{label}.reason_code is invalid for an omitted phrase.")
            if str(phrase.get("evidence_status", "")) == "verified" and reason_code == "unsupported":
                errors.append(f"{label}.reason_code unsupported is reserved for unsupported evidence.")
            continue

        if not realizations:
            errors.append(f"{label} used phrases require at least one realization.")
        if str(phrase.get("evidence_status", "")) != "verified" or not phrase.get("fact_refs"):
            errors.append(f"{label} cannot use a phrase without direct verified fact evidence.")

        placements_seen: set[str] = set()
        placement_text: dict[str, str] = {}
        for realization_index, realization in enumerate(realizations, start=1):
            realization_label = f"{label}.realizations[{realization_index}]"
            placement, realization_text, tokens = validate_v2_realization(
                realization,
                realization_label,
                str(phrase.get("source_text", "")),
                title,
                highlights,
                errors,
            )
            if placement in placements_seen:
                errors.append(f"{label} may contain at most one realization per field.")
            placements_seen.add(placement)
            placement_text[placement] = realization_text
            realized_tokens.update(tokens)
            if placement == "title":
                title_realizations_by_phrase.setdefault(phrase_id, []).append(realization_text)
                rank = priorities.get(str(phrase.get("priority", "")), len(priorities))
                title_priorities.append((phrase_id, rank))

        if "title" in placement_text and "item_highlights" in placement_text:
            if not has_information_increment(
                placement_text["title"], placement_text["item_highlights"]
            ):
                errors.append(
                    f"{label} cross-field reuse must add verified information in Item Highlights."
                )
        if "title" in placement_text and reason_code != "retained":
            errors.append(f"{label}.reason_code must be retained when the phrase is used in Title.")
        elif "title" not in placement_text:
            is_moved_dual = (
                str(phrase.get("priority", "")) == "dual_value_differentiator"
                and reason_code in PRIORITY_EXCEPTION_CODES
            )
            if reason_code != "retained" and not is_moved_dual:
                errors.append(
                    f"{label}.reason_code must be retained unless a dual-value differentiator "
                    "moves under an allowed priority exception."
                )

        semantic_group_id = str(phrase.get("semantic_group_id", "")).strip()
        semantic_relation = str(phrase.get("semantic_relation", "")).strip()
        if (
            semantic_group_id
            and semantic_relation in {"primary", "synonym", "functional_alias"}
            and "title" in placement_text
        ):
            title_semantic_groups.setdefault(semantic_group_id, []).append(phrase_id)

    missing_ids = sorted(set(phrases) - seen)
    if missing_ids:
        errors.append(f"{option_label} is missing phrase allocations: {', '.join(missing_ids)}")
    for group_id, phrase_ids in title_semantic_groups.items():
        if len(phrase_ids) > 1:
            errors.append(
                f"{option_label} places multiple category aliases from {group_id} in Title: "
                + ", ".join(phrase_ids)
            )

    dual_phrases = sorted(
        (
            phrase for phrase in phrases.values()
            if phrase.get("priority") == "dual_value_differentiator"
        ),
        key=lambda phrase: int(phrase.get("dual_value_rank", 10**6)),
    )
    dual_title_realizations: list[str] = []
    for phrase in dual_phrases:
        phrase_id = str(phrase.get("id"))
        allocation = allocation_by_phrase.get(phrase_id, {})
        title_realizations = title_realizations_by_phrase.get(phrase_id, [])
        if title_realizations:
            dual_title_realizations.extend(title_realizations)
            continue
        label = f"{option_label}.reference_phrase_allocation[{phrase_id}]"
        reason_code = str(allocation.get("reason_code", "")).strip()
        if reason_code not in PRIORITY_EXCEPTION_CODES:
            errors.append(
                f"{label} must place the higher-priority dual-value differentiator in Title "
                "or record an allowed exception."
            )
        validate_title_fit_evaluation(
            allocation,
            label,
            components,
            str(phrase.get("source_text", "")),
            dual_title_realizations,
            reason_code,
            errors,
        )
    sku_fit_base_title = validate_sku_fit_evaluation(
        option, option_label, components, dual_title_realizations, errors
    )
    realized_tokens.update(
        validate_additional_phrases(option, option_label, title, highlights, errors)
    )
    candidate_tokens = evidence_tokens(f"{title} {highlights}")
    if realized_tokens != candidate_tokens:
        errors.append(
            f"{option_label} contains content tokens not covered exactly by semantic realizations "
            "or additional_verified_phrases."
        )
    return sku_fit_base_title


def validate_core_keyword_selection(generation: dict, errors: list[str]) -> str:
    selection = generation.get("core_keyword_selection")
    if not isinstance(selection, dict):
        errors.append("title_options_generation.core_keyword_selection is required for v3 and v4.")
        return ""

    candidates = selection.get("candidates")
    if not isinstance(candidates, list):
        errors.append("core_keyword_selection.candidates must be an array.")
        return ""

    eligible_keywords: list[tuple[int, str]] = []
    seen_orders: set[int] = set()
    for index, candidate in enumerate(candidates, start=1):
        label = f"core_keyword_selection.candidates[{index}]"
        if not isinstance(candidate, dict):
            errors.append(f"{label} must be an object.")
            continue
        keyword = str(candidate.get("keyword", "")).strip()
        if not keyword:
            errors.append(f"{label}.keyword is required.")
        input_order = candidate.get("input_order")
        if not isinstance(input_order, int) or input_order <= 0:
            errors.append(f"{label}.input_order must be a positive integer.")
        elif input_order in seen_orders:
            errors.append(f"{label}.input_order is duplicated: {input_order}.")
        else:
            seen_orders.add(input_order)

        language_match = candidate.get("marketplace_language_match")
        category_match = candidate.get("category_match")
        listing_eligible = candidate.get("listing_eligible")
        for field, value in (
            ("marketplace_language_match", language_match),
            ("category_match", category_match),
            ("listing_eligible", listing_eligible),
        ):
            if not isinstance(value, bool):
                errors.append(f"{label}.{field} must be boolean.")

        category_refs = string_list(
            candidate.get("category_fact_refs", []), f"{label}.category_fact_refs", errors
        )
        if category_match is True and not category_refs:
            errors.append(f"{label}.category_fact_refs is required when category_match is true.")

        traffic_status = str(candidate.get("traffic_status", "")).strip()
        if traffic_status not in TRAFFIC_STATUSES:
            errors.append(f"{label}.traffic_status is invalid.")
        evidence = candidate.get("traffic_evidence")
        if not isinstance(evidence, list):
            errors.append(f"{label}.traffic_evidence must be an array.")
            evidence = []
        has_metric = False
        has_user_confirmation = False
        for evidence_index, item in enumerate(evidence, start=1):
            evidence_label = f"{label}.traffic_evidence[{evidence_index}]"
            if not isinstance(item, dict):
                errors.append(f"{evidence_label} must be an object.")
                continue
            evidence_type = str(item.get("type", "")).strip()
            source = str(item.get("source", "")).strip()
            if not source:
                errors.append(f"{evidence_label}.source is required.")
            if evidence_type == "metric":
                metric = str(item.get("metric", "")).strip()
                value = item.get("value")
                if metric not in TRAFFIC_METRICS:
                    errors.append(f"{evidence_label}.metric is not accepted traffic evidence.")
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
                    errors.append(f"{evidence_label}.value must be a positive number.")
                if metric in TRAFFIC_METRICS and isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                    has_metric = True
            elif evidence_type == "user_explicit":
                if source != "user":
                    errors.append(f"{evidence_label}.source must be user for user_explicit evidence.")
                else:
                    has_user_confirmation = True
            else:
                errors.append(f"{evidence_label}.type must be metric or user_explicit.")

        expected_traffic = (
            "verified_metric" if has_metric
            else "user_confirmed" if has_user_confirmation
            else "not_verified"
        )
        if traffic_status in TRAFFIC_STATUSES and traffic_status != expected_traffic:
            errors.append(f"{label}.traffic_status must be {expected_traffic} for its evidence.")

        expected_eligible = bool(
            keyword
            and language_match is True
            and category_match is True
            and listing_eligible is True
            and expected_traffic != "not_verified"
        )
        if candidate.get("eligible") is not expected_eligible:
            errors.append(f"{label}.eligible is inconsistent with language, category, traffic, or Listing eligibility.")
        reason = str(candidate.get("reason", "")).strip()
        if not reason or not CHINESE_RE.search(reason):
            errors.append(f"{label}.reason must be a non-empty Chinese explanation.")
        if expected_eligible and isinstance(input_order, int):
            eligible_keywords.append((input_order, keyword))

    if seen_orders and seen_orders != set(range(1, len(candidates) + 1)):
        errors.append("core_keyword_selection input_order values must be contiguous starting at 1.")

    selected_keyword = str(selection.get("selected_keyword", "")).strip()
    expected_keyword = min(eligible_keywords)[1] if eligible_keywords else ""
    if selected_keyword != expected_keyword:
        errors.append(
            "core_keyword_selection.selected_keyword must be the first eligible user keyword "
            "in input order."
        )
    expected_status = "selected" if expected_keyword else "not_applicable"
    if selection.get("status") != expected_status:
        errors.append(f"core_keyword_selection.status must be {expected_status}.")
    if selection.get("selection_rule") != "first_eligible_user_input":
        errors.append("core_keyword_selection.selection_rule must be first_eligible_user_input.")
    if selection.get("preservation_mode") != "all_tokens_same_order_normalization_only":
        errors.append(
            "core_keyword_selection.preservation_mode must be "
            "all_tokens_same_order_normalization_only."
        )
    reason = str(selection.get("reason", "")).strip()
    if not reason or not CHINESE_RE.search(reason):
        errors.append("core_keyword_selection.reason must be a non-empty Chinese explanation.")
    return selected_keyword


def normalized_candidate_signature(title: str, highlights: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Ignore presentation-only changes while retaining the Title/Highlights boundary."""
    return (
        tuple(sorted(TITLE_VALIDATOR.preservation_tokens(title))),
        tuple(sorted(TITLE_VALIDATOR.preservation_tokens(highlights))),
    )


def validate_quality_assessment(option: dict, option_label: str, errors: list[str]) -> None:
    assessment = option.get("quality_assessment")
    if not isinstance(assessment, dict):
        errors.append(f"{option_label}.quality_assessment is required for new v4 options.")
        return
    expected_keys = set(QUALITY_SCORE_LIMITS) | {"total"}
    if set(assessment) != expected_keys:
        errors.append(f"{option_label}.quality_assessment must contain exactly the internal score fields.")
        return
    component_total = 0
    for key, limit in QUALITY_SCORE_LIMITS.items():
        value = assessment.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= limit:
            errors.append(f"{option_label}.quality_assessment.{key} must be an integer from 0 to {limit}.")
            continue
        component_total += value
    if assessment.get("total") != component_total:
        errors.append(f"{option_label}.quality_assessment.total must equal its five component scores.")


def validate_title_pair_coverage(
    option: dict, option_label: str, generation: dict, errors: list[str]
) -> None:
    """Require v4 to optimize the two searchable fields as one evidence-backed pair."""
    fact_pool = generation.get("title_pair_fact_pool")
    audit = option.get("title_pair_coverage_audit")
    if not isinstance(fact_pool, list) or not fact_pool:
        errors.append("title_options_generation.title_pair_fact_pool must be a non-empty array for v4.")
        return
    if not isinstance(audit, list):
        errors.append(f"{option_label}.title_pair_coverage_audit must be an array.")
        return

    facts: dict[str, dict] = {}
    highlight_candidates: dict[str, dict] = {}
    for index, fact in enumerate(fact_pool, start=1):
        label = f"title_pair_fact_pool[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{label} must be an object.")
            continue
        fact_id = str(fact.get("id", "")).strip()
        if not re.fullmatch(r"TPF-\d{2,}", fact_id) or fact_id in facts:
            errors.append(f"{label}.id must be a unique TPF- identifier.")
            continue
        if not str(fact.get("text", "")).strip():
            errors.append(f"{label}.text is required.")
        if not string_list(fact.get("fact_refs"), f"{label}.fact_refs", errors):
            errors.append(f"{label}.fact_refs must contain direct product evidence.")
        factor = str(fact.get("decision_factor", "")).strip()
        if factor not in DECISION_FACTORS:
            errors.append(f"{label}.decision_factor is invalid.")
        value = str(fact.get("decision_value", "")).strip()
        if value not in DECISION_VALUES:
            errors.append(f"{label}.decision_value is invalid.")
        character_cost = fact.get("character_cost")
        if not isinstance(character_cost, int) or character_cost < 1:
            errors.append(f"{label}.character_cost must be a positive integer.")
        string_list(fact.get("keyword_refs", []), f"{label}.keyword_refs", errors)
        string_list(fact.get("selling_point_refs", []), f"{label}.selling_point_refs", errors)
        facts[fact_id] = fact
        candidate = fact.get("highlight_candidate")
        requires_candidate = (
            value in {"required", "high"}
            and factor not in {"identity", "variant"}
        )
        if candidate is None and requires_candidate:
            errors.append(f"{label}.highlight_candidate is required for high-priority non-identity facts.")
        elif candidate is not None:
            if not isinstance(candidate, dict):
                errors.append(f"{label}.highlight_candidate must be an object.")
            else:
                candidate_text = str(candidate.get("text", "")).strip()
                candidate_refs = candidate.get("fact_refs")
                candidate_cost = candidate.get("character_cost")
                candidate_reason = str(candidate.get("title_information_gain", "")).strip()
                if not candidate_text:
                    errors.append(f"{label}.highlight_candidate.text is required.")
                if not isinstance(candidate_refs, list) or not candidate_refs or not set(candidate_refs).issubset(set(fact.get("fact_refs") or [])):
                    errors.append(f"{label}.highlight_candidate.fact_refs must be direct evidence from the fact.")
                if candidate_cost != len(candidate_text):
                    errors.append(f"{label}.highlight_candidate.character_cost must equal its Unicode character length.")
                if not candidate_reason or not CHINESE_RE.search(candidate_reason):
                    errors.append(f"{label}.highlight_candidate.title_information_gain must be a Chinese explanation.")
                highlight_candidates[fact_id] = candidate

    title = str(option.get("title", ""))
    highlights = str(option.get("item_highlights", ""))
    rows: dict[str, dict] = {}
    highlight_factors: set[str] = set()
    for index, row in enumerate(audit, start=1):
        label = f"{option_label}.title_pair_coverage_audit[{index}]"
        if not isinstance(row, dict):
            errors.append(f"{label} must be an object.")
            continue
        fact_id = str(row.get("fact_id", "")).strip()
        if fact_id not in facts or fact_id in rows:
            errors.append(f"{label}.fact_id must reference a unique title_pair_fact_pool item.")
            continue
        rows[fact_id] = row
        placement = str(row.get("placement", "")).strip()
        if placement not in TITLE_PAIR_PLACEMENTS:
            errors.append(f"{label}.placement is invalid.")
            continue
        text = str(row.get("text", "")).strip()
        reason = str(row.get("reason", "")).strip()
        if not reason or not CHINESE_RE.search(reason):
            errors.append(f"{label}.reason must be a non-empty Chinese explanation.")
        if placement == "omitted":
            if text:
                errors.append(f"{label}.text must be empty when placement is omitted.")
            if str(row.get("omission_reason_code", "")).strip() not in OMISSION_REASON_CODES - {"unsupported"}:
                errors.append(f"{label}.omission_reason_code is required for omitted verified facts.")
        else:
            field = title if placement == "title" else highlights
            if not text or not TITLE_VALIDATOR.contains_component(field, text):
                errors.append(f"{label}.text must appear in its declared field.")
            if placement == "item_highlights":
                highlight_factors.add(str(facts[fact_id].get("decision_factor", "")))

    if set(rows) != set(facts):
        errors.append(f"{option_label}.title_pair_coverage_audit must allocate every title-pair fact.")
    high_priority = [
        fact_id for fact_id, fact in facts.items()
        if fact.get("decision_value") in {"required", "high"}
        and fact.get("decision_factor") not in {"identity", "variant"}
    ]
    omitted_high = [fact_id for fact_id in high_priority if rows.get(fact_id, {}).get("placement") == "omitted"]
    if omitted_high:
        errors.append(f"{option_label} omits high-priority title-pair facts: {', '.join(omitted_high)}")
    if len(high_priority) >= 3 and len(highlight_factors) < 2:
        errors.append(
            f"{option_label} must cover at least two distinct purchase-decision factors in Item Highlights when facts are dense."
        )
    if facts and not any(row.get("placement") == "item_highlights" for row in rows.values()):
        errors.append(f"{option_label} must add verified information in Item Highlights.")
    validate_highlight_capacity(
        option, option_label, highlight_candidates, title, highlights, rows, errors
    )


def validate_highlight_capacity(
    option: dict, option_label: str, candidates: dict[str, dict],
    title: str, highlights: str, rows: dict[str, dict], errors: list[str],
) -> None:
    """Reject sparse Highlights when the fact packet proves richer complementary copy exists."""
    capacity = option.get("highlight_capacity")
    if not isinstance(capacity, dict):
        errors.append(f"{option_label}.highlight_capacity is required for v4 options.")
        return
    available = [
        fact_id for fact_id, candidate in candidates.items()
        if not TITLE_VALIDATOR.contains_component(title, str(candidate.get("text", "")))
    ]
    declared = capacity.get("available_highlight_candidate_ids")
    if not isinstance(declared, list) or set(declared) != set(available) or len(declared) != len(set(declared)):
        errors.append(f"{option_label}.highlight_capacity.available_highlight_candidate_ids must match usable fact-pool candidates.")
    usable = sum(int(candidates[fact_id]["character_cost"]) for fact_id in available)
    if available:
        usable += 2 * (len(available) - 1)
    if capacity.get("usable_highlight_characters") != usable:
        errors.append(f"{option_label}.highlight_capacity.usable_highlight_characters is not reproducible from candidates.")
    target = min(100, usable) if len(available) >= 3 and usable >= 100 else usable
    if capacity.get("target_highlight_characters") != target:
        errors.append(f"{option_label}.highlight_capacity.target_highlight_characters must use the dynamic target rule.")
    actual = len(highlights)
    if capacity.get("actual_highlight_characters") != actual:
        errors.append(f"{option_label}.highlight_capacity.actual_highlight_characters must equal Item Highlights length.")
    status = str(capacity.get("capacity_status", "")).strip()
    if status not in HIGHLIGHT_CAPACITY_STATUSES:
        errors.append(f"{option_label}.highlight_capacity.capacity_status is invalid.")
    uncovered = [
        fact_id for fact_id in available
        if rows.get(fact_id, {}).get("placement") != "item_highlights"
    ]
    reasons = capacity.get("unallocated_candidates")
    if not isinstance(reasons, list):
        errors.append(f"{option_label}.highlight_capacity.unallocated_candidates must be an array.")
        reasons = []
    reason_ids = {str(item.get("fact_id", "")).strip() for item in reasons if isinstance(item, dict)}
    if set(uncovered) != reason_ids:
        errors.append(f"{option_label}.highlight_capacity must explain every usable candidate not placed in Item Highlights.")
    for item in reasons:
        if not isinstance(item, dict):
            errors.append(f"{option_label}.highlight_capacity.unallocated_candidates contains an invalid entry.")
            continue
        if str(item.get("reason_code", "")).strip() not in OMISSION_REASON_CODES - {"unsupported"}:
            errors.append(f"{option_label}.highlight_capacity unallocated candidate needs an allowed reason_code.")
        reason = str(item.get("reason", "")).strip()
        if not reason or not CHINESE_RE.search(reason):
            errors.append(f"{option_label}.highlight_capacity unallocated candidate needs a Chinese reason.")
    if not uncovered and actual < target:
        errors.append(f"{option_label} Item Highlights is sparse despite sufficient verified fact capacity ({actual}/{target}).")
    if status == "achieved" and (uncovered or actual < target):
        errors.append(f"{option_label}.highlight_capacity cannot be achieved when usable evidence remains unallocated or the target is missed.")
    if status == "evidence_limited" and not uncovered:
        errors.append(f"{option_label}.highlight_capacity may be evidence_limited only when documented candidate exclusions remain.")


def validate_quality_generation(options: list[dict], phrases: dict[str, dict], errors: list[str]) -> None:
    seen_strategies: set[str] = set()
    seen_focus_sets: set[tuple[str, ...]] = set()
    seen_signatures: dict[tuple[tuple[str, ...], tuple[str, ...]], int] = {}
    ranked_totals: list[tuple[int, int, int]] = []
    for index, option in enumerate(options, start=1):
        if not isinstance(option, dict):
            continue
        label = f"title_options_2026[{index}]"
        strategy = str(option.get("generation_strategy", "")).strip()
        if strategy not in QUALITY_GENERATION_STRATEGIES:
            errors.append(f"{label}.generation_strategy must be one of: " + ", ".join(QUALITY_GENERATION_STRATEGIES) + ".")
        elif strategy in seen_strategies:
            errors.append(f"{label}.generation_strategy must be unique across the three options.")
        else:
            seen_strategies.add(strategy)

        focus_ids = option.get("strategy_focus_phrase_ids")
        coverage = option.get("evidence_coverage")
        coverage_valid = isinstance(coverage, list) and bool(coverage) and not any(
            not isinstance(item, str) or not item.strip() for item in coverage
        )
        coverage_refs = set(coverage) if coverage_valid else set()
        if not isinstance(focus_ids, list) or not focus_ids or any(
            not isinstance(item, str) or item not in phrases for item in focus_ids
        ) or len(set(focus_ids)) != len(focus_ids):
            errors.append(f"{label}.strategy_focus_phrase_ids must be a non-empty unique list of reference phrase IDs.")
        else:
            focus_signature = tuple(sorted(focus_ids))
            if focus_signature in seen_focus_sets:
                errors.append(f"{label}.strategy_focus_phrase_ids must differ from every other option.")
            seen_focus_sets.add(focus_signature)
            allocations = {
                str(item.get("phrase_id", "")).strip(): item
                for item in option.get("reference_phrase_allocation", [])
                if isinstance(item, dict)
            }
            for phrase_id in focus_ids:
                fact_refs = set(phrases[phrase_id].get("fact_refs") or [])
                if not fact_refs.intersection(coverage_refs):
                    errors.append(
                        f"{label}.evidence_coverage must cite direct fact evidence for focus phrase {phrase_id}."
                    )
                allocation = allocations.get(phrase_id)
                realizations = allocation.get("realizations") if isinstance(allocation, dict) else []
                if not isinstance(realizations, list) or not realizations:
                    errors.append(
                        f"{label}.strategy_focus_phrase_ids must identify a phrase realized in Title or Item Highlights."
                    )

        rationale = str(option.get("quality_rationale", "")).strip()
        if not rationale or not CHINESE_RE.search(rationale):
            errors.append(f"{label}.quality_rationale must be a non-empty Chinese explanation.")
        if not coverage_valid:
            errors.append(f"{label}.evidence_coverage must be a non-empty list of evidence references.")
        fallback = option.get("fallback_verified_fact")
        if fallback is not None:
            if not isinstance(fallback, dict):
                errors.append(f"{label}.fallback_verified_fact must be an object when used.")
            else:
                if not str(fallback.get("text", "")).strip():
                    errors.append(f"{label}.fallback_verified_fact.text is required.")
                if not string_list(fallback.get("fact_refs"), f"{label}.fallback_verified_fact.fact_refs", errors):
                    errors.append(f"{label}.fallback_verified_fact.fact_refs must contain direct evidence.")
                reason = str(fallback.get("reason", "")).strip()
                if not reason or not CHINESE_RE.search(reason):
                    errors.append(f"{label}.fallback_verified_fact.reason must be a Chinese explanation.")
        validate_quality_assessment(option, label, errors)
        assessment = option.get("quality_assessment") if isinstance(option.get("quality_assessment"), dict) else {}
        rank = option.get("rank")
        option_number = option.get("option")
        if not isinstance(rank, int) or rank not in {1, 2, 3}:
            errors.append(f"{label}.rank must be an integer from 1 to 3.")
        if not isinstance(option_number, int) or option_number not in {1, 2, 3}:
            errors.append(f"{label}.option must be an integer from 1 to 3.")
        if isinstance(rank, int) and isinstance(option_number, int):
            ranked_totals.append((rank, int(assessment.get("total", -1)), option_number))

        signature = normalized_candidate_signature(
            str(option.get("title", "")), str(option.get("item_highlights", ""))
        )
        previous = seen_signatures.get(signature)
        if previous is not None:
            errors.append(
                f"{label} is materially identical to title_options_2026[{previous}]; "
                "score, punctuation, capitalization, word order, or unit spacing alone cannot create a new option."
            )
        else:
            seen_signatures[signature] = index

    if seen_strategies != set(QUALITY_GENERATION_STRATEGIES):
        errors.append("New v4 options must include each required generation_strategy exactly once.")
    if sorted(rank for rank, _, _ in ranked_totals) != [1, 2, 3]:
        errors.append("New v4 options must use each rank exactly once.")
    else:
        ordered = sorted(ranked_totals)
        if any(ordered[index][1] < ordered[index + 1][1] for index in range(len(ordered) - 1)):
            errors.append("New v4 option ranks must follow descending internal quality_assessment totals.")
        first = next((option for option in options if option.get("rank") == 1), None)
        if not isinstance(first, dict) or first.get("status") != "recommended_for_current_upload":
            errors.append("New v4 rank 1 must be recommended_for_current_upload.")


def validate_title_options(
    data: dict,
    legacy_title: str,
    errors: list[str],
    *,
    allow_legacy_title_method: bool = False,
) -> None:
    options = data.get("title_options_2026")
    diagnostic = data.get("diagnostic") if isinstance(data.get("diagnostic"), dict) else {}
    generation = data.get("title_options_generation")
    if not isinstance(generation, dict):
        errors.append("title_options_generation is required before validating 2026 options.")
        return
    method = str(generation.get("method", "")).strip()
    if generation.get("reference_title") != legacy_title:
        errors.append("title_options_generation.reference_title must equal legacy_listing.title.")
    if allow_legacy_title_method:
        if method and method not in REFERENCE_METHODS:
            errors.append(
                "Archived title_options_generation.method must be "
                f"empty, {REFERENCE_METHOD_V1}, {REFERENCE_METHOD_V2}, {REFERENCE_METHOD_V3}, or {REFERENCE_METHOD_V4}."
            )
    elif method != REFERENCE_METHOD_V4:
        errors.append(
            "New 2026 title generation must use "
            f"title_options_generation.method={REFERENCE_METHOD_V4}; "
            "empty and v1-v3 methods are archive-read-only."
        )
    required_core_keyword = (
        validate_core_keyword_selection(generation, errors)
        if method in {REFERENCE_METHOD_V3, REFERENCE_METHOD_V4} else ""
    )
    if options == []:
        reason = str(diagnostic.get("title_options_2026_block_reason", "")).strip()
        if not reason:
            errors.append(
                "Empty title_options_2026 requires diagnostic.title_options_2026_block_reason."
            )
        return
    if not isinstance(options, list) or len(options) != 3:
        errors.append("title_options_2026 must contain exactly 3 options or be explicitly blocked.")
        return

    phrases = (
        validate_reference_phrase_analysis(generation, legacy_title, errors, method)
        if method in REFERENCE_METHODS else {}
    )

    # Archived reports remain readable, while every new v4 report must prove that its
    # three options are materially different, evidence-backed strategies.
    if method == REFERENCE_METHOD_V4 and not allow_legacy_title_method:
        validate_quality_generation(options, phrases, errors)

    for index, option in enumerate(options, start=1):
        if not isinstance(option, dict):
            errors.append(f"title_options_2026[{index}] must be an object.")
            continue
        components = option.get("title_components")
        if not isinstance(components, dict):
            errors.append(f"title_options_2026[{index}].title_components is required.")
            continue
        sku_fit_base_title = ""
        if method in REFERENCE_METHODS_V2_PLUS:
            sku_fit_base_title = validate_phrase_allocation_v2(
                option, index, phrases, components, errors
            )
        if method == REFERENCE_METHOD_V4:
            validate_title_pair_coverage(option, f"title_options_2026[{index}]", generation, errors)
        result = TITLE_VALIDATOR.validate(
            str(option.get("title", "")),
            str(option.get("item_highlights", "")),
            str(data.get("marketplace", "")),
            brand=str(components.get("brand", "")),
            core_product_phrase=str(components.get("core_product_phrase", "")),
            differentiator=str(components.get("differentiator", "")),
            sku_attributes=components.get("sku_attributes") or [],
            sku_attribute_placement=str(option.get("sku_attribute_placement", "")),
            sku_fit_base_title=sku_fit_base_title,
            required_core_keyword=required_core_keyword,
        )
        if not result["valid"]:
            for message in result["errors"]:
                errors.append(f"title_options_2026[{index}]: {message}")
        if method == REFERENCE_METHOD_V1:
            validate_phrase_allocation(option, index, phrases, errors)


def validate_report(
    data: object,
    artifact: object | None = None,
    *,
    allow_legacy_title_method: bool = False,
) -> dict:
    errors: list[str] = []
    if not isinstance(data, dict):
        return {"ok": False, "errors": ["Report root must be an object."]}

    legacy = data.get("legacy_generation")
    if not isinstance(legacy, dict):
        return {"ok": False, "errors": ["legacy_generation is required."]}

    if legacy.get("source_skill") != SOURCE_SKILL:
        errors.append(f"legacy_generation.source_skill must be {SOURCE_SKILL}.")
    if legacy.get("source_skill_path") != SOURCE_SKILL_PATH:
        errors.append(f"legacy_generation.source_skill_path must be {SOURCE_SKILL_PATH}.")
    if legacy.get("status") != "complete":
        errors.append("legacy_generation.status must be complete.")
    if data.get("listing_generation_source") != SOURCE_SKILL:
        errors.append(f"listing_generation_source must be {SOURCE_SKILL}.")

    mode = str(data.get("mode", "")).upper()
    asin = str(data.get("asin", "")).strip().upper()
    if re.fullmatch(r"B0[A-Z0-9]{8}", asin) and mode != "B":
        errors.append("mode must be B for an ASIN Listing optimization.")
    elif mode not in {"A", "B"}:
        errors.append("mode must be A or B.")
    if str(legacy.get("mode", "")).upper() != mode:
        errors.append("legacy_generation.mode must match report mode.")

    validate_manifest(legacy.get("input_manifest"), errors)
    legacy_listing = validate_listing(legacy.get("legacy_listing"), errors)
    if not isinstance(legacy.get("keyword_priority"), (dict, list)):
        errors.append("legacy_generation.keyword_priority must be structured data.")
    if not isinstance(legacy.get("keyword_coverage"), (dict, list)):
        errors.append("legacy_generation.keyword_coverage must be structured data.")
    if not isinstance(legacy.get("keyword_gaps"), (dict, list)):
        errors.append("legacy_generation.keyword_gaps must be structured data.")
    if not isinstance(legacy.get("limitations"), list):
        errors.append("legacy_generation.limitations must be an array.")
    if data.get("listing") != legacy_listing:
        errors.append("listing must exactly equal legacy_generation.legacy_listing.")

    validate_invocation_evidence(
        legacy, artifact, legacy_listing, str(data.get("asin", "")).strip(), errors
    )

    artifact_path = str(legacy.get("artifact_path", "")).strip()
    if not artifact_path:
        errors.append("legacy_generation.artifact_path is required.")
    elif Path(artifact_path).name != f"legacy-listing-result-{str(data.get('asin', '')).strip()}.json":
        errors.append("legacy_generation.artifact_path must use the required ASIN filename.")
    if artifact is not None:
        if not isinstance(artifact, dict):
            errors.append("Legacy artifact root must be an object.")
        else:
            for field in (
                "source_skill",
                "source_skill_path",
                "mode",
                "status",
                "completed_at",
                "input_manifest",
                "keyword_priority",
                "keyword_coverage",
                "keyword_gaps",
                "limitations",
            ):
                if artifact.get(field) != legacy.get(field):
                    errors.append(f"Legacy artifact {field} does not match legacy_generation.")
            if artifact.get("legacy_listing") != legacy_listing:
                errors.append("Legacy artifact legacy_listing does not match legacy_generation.")
            if isinstance(legacy.get("execution_provenance"), dict) and artifact.get("execution_provenance") != legacy.get("execution_provenance"):
                errors.append("Legacy artifact execution_provenance does not match legacy_generation.")

    legacy_completed = parse_datetime(legacy.get("completed_at"), "legacy_generation.completed_at", errors)
    generation = data.get("title_options_generation")
    options = data.get("title_options_2026")
    if isinstance(generation, dict) and generation.get("reference_title") != legacy_listing.get("title"):
        errors.append("title_options_generation.reference_title must exactly equal legacy_generation.legacy_listing.title.")
    if options:
        if isinstance(generation, dict):
            title_started = parse_datetime(
                generation.get("started_at"), "title_options_generation.started_at", errors
            )
            if legacy_completed and title_started:
                try:
                    if title_started < legacy_completed:
                        errors.append("2026 title generation started before legacy generation completed.")
                except TypeError:
                    errors.append("Generation timestamps must use compatible timezone formats.")
        validate_title_options(
            data,
            str(legacy_listing.get("title", "")),
            errors,
            allow_legacy_title_method=allow_legacy_title_method,
        )
    else:
        validate_title_options(
            data,
            str(legacy_listing.get("title", "")),
            errors,
            allow_legacy_title_method=allow_legacy_title_method,
        )

    sequence = data.get("generation_sequence")
    required_sequence = ["evidence_collection", "legacy_listing", "title_options_2026"]
    if sequence != required_sequence:
        errors.append(f"generation_sequence must equal {required_sequence}.")

    return {
        "ok": not errors,
        "source_skill": legacy.get("source_skill", ""),
        "mode": mode,
        "input_sections": list(INPUT_SECTIONS),
        "title_option_count": len(options) if isinstance(options, list) else 0,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to listing report JSON")
    parser.add_argument("--legacy-artifact", help="Path to legacy-listing-result JSON")
    parser.add_argument(
        "--allow-legacy-title-method",
        action="store_true",
        help="Read archived 2026 title reports that predate the mandatory v4 allocation method.",
    )
    parser.add_argument("--output", help="Optional validation result JSON")
    args = parser.parse_args()

    report = json.loads(Path(args.input).read_text(encoding="utf-8"))
    artifact = None
    if args.legacy_artifact:
        artifact = json.loads(Path(args.legacy_artifact).read_text(encoding="utf-8"))
    result = validate_report(
        report,
        artifact,
        allow_legacy_title_method=args.allow_legacy_title_method,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
