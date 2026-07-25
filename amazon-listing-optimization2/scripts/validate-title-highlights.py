#!/usr/bin/env python3
"""Validate a July 2026 Amazon Title + Item Highlights pair."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter


TITLE_LIMIT = 75
HIGHLIGHTS_LIMIT = 125
PROHIBITED_TITLE_CHARACTERS = set("!$?_{}^¬¦")
HARD_PROMOTIONAL_PHRASES = (
    "#1",
    "100% quality guarantee",
    "100%ige qualitätsgarantie",
    "best seller",
    "bestseller",
    "free shipping",
    "kostenloser versand",
    "livraison gratuite",
    "spedizione gratuita",
    "envío gratis",
    "envio gratis",
    "frete grátis",
)
SUBJECTIVE_PHRASES = (
    "best",
    "beste",
    "bestes",
    "ideal",
    "perfect",
    "perfekt",
    "top rated",
    "top-produkt",
)
REFINEMENT_ONLY_MODIFIERS = {
    "strong", "powerful", "soft", "comfortable",
    "stark", "starke", "starken", "weich", "bequem",
    "puissant", "puissante", "doux", "douce", "confortable",
    "potente", "potenti", "soffice", "morbido", "morbida", "comodo", "comoda",
    "fuerte", "potente", "suave", "cómodo", "cómoda",
    "forte", "macio", "macia", "confortável",
}
STOPWORDS = {
    "and", "or", "the", "a", "an", "for", "with", "of", "in", "to",
    "und", "oder", "der", "die", "das", "ein", "eine", "für", "mit", "von", "im",
    "et", "ou", "le", "la", "les", "un", "une", "pour", "avec", "de", "des",
    "e", "o", "a", "il", "lo", "per", "con", "di", "da",
    "y", "o", "el", "la", "los", "las", "para", "con", "de",
}


def normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value.strip())


def words(value: str) -> list[str]:
    return [
        token.casefold()
        for token in re.findall(r"[^\W\d_]+|\d+(?:[.,]\d+)?", value, flags=re.UNICODE)
    ]


def content_words(value: str) -> set[str]:
    return {
        token
        for token in words(value)
        if len(token) >= 4 and token not in STOPWORDS and not token.isdigit()
    }


def semantic_overlap_pairs(
    title_words: set[str], highlight_words: set[str]
) -> list[tuple[str, str]]:
    candidates: set[tuple[str, str]] = set()
    for title_word in title_words:
        for highlight_word in highlight_words:
            if title_word == highlight_word:
                continue
            shorter, longer = sorted((title_word, highlight_word), key=len)
            if len(shorter) >= 6 and shorter in longer:
                candidates.add((title_word, highlight_word))
                continue
            common_prefix = 0
            for index, (left, right) in enumerate(zip(title_word, highlight_word)):
                if left != right:
                    break
                common_prefix = index + 1
            common_suffix = 0
            for index, (left, right) in enumerate(zip(reversed(title_word), reversed(highlight_word))):
                if left != right:
                    break
                common_suffix = index + 1
            if common_prefix >= 5 and common_suffix >= 4:
                candidates.add((title_word, highlight_word))
    return sorted(candidates)


def split_highlight_phrases(value: str) -> list[str]:
    return [
        phrase.strip()
        for phrase in re.split(r"[,;，；、]", value)
        if phrase.strip()
    ]


def cross_field_relations(title: str, highlights: str) -> list[dict]:
    title_terms = content_words(title)
    phrases = split_highlight_phrases(highlights)
    relations: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()

    for phrase in phrases:
        phrase_terms = content_words(phrase)
        phrase_tokens = words(phrase)
        numeric_details = sorted({token for token in phrase_tokens if any(char.isdigit() for char in token)})

        for shared_term in sorted(title_terms.intersection(phrase_terms)):
            added_terms = sorted(phrase_terms - title_terms)
            concrete_terms = [
                term for term in added_terms if term not in REFINEMENT_ONLY_MODIFIERS
            ]
            if numeric_details or concrete_terms:
                relation_type = "qualified_refinement_candidate"
            elif added_terms:
                relation_type = "semantic_overlap_review"
            else:
                relation_type = "redundant_exact"

            key = (relation_type, shared_term, shared_term, phrase.casefold())
            if key in seen:
                continue
            seen.add(key)
            relations.append(
                {
                    "type": relation_type,
                    "title_term": shared_term,
                    "item_highlights_term": shared_term,
                    "item_highlights_phrase": phrase,
                    "added_detail": sorted(set(numeric_details + added_terms)),
                }
            )

        for title_term, highlight_term in semantic_overlap_pairs(title_terms, phrase_terms):
            key = (
                "semantic_overlap_review",
                title_term,
                highlight_term,
                phrase.casefold(),
            )
            if key in seen:
                continue
            seen.add(key)
            relations.append(
                {
                    "type": "semantic_overlap_review",
                    "title_term": title_term,
                    "item_highlights_term": highlight_term,
                    "item_highlights_phrase": phrase,
                    "added_detail": [],
                }
            )

    return relations


def validate(title_value: str, highlights_value: str, marketplace: str) -> dict:
    title = normalize(title_value)
    highlights = normalize(highlights_value)
    errors: list[str] = []
    warnings: list[str] = []

    if not title:
        errors.append("Title is empty.")
    if not highlights:
        errors.append("Item Highlights is empty.")
    if len(title) > TITLE_LIMIT:
        errors.append(f"Title has {len(title)} characters; limit is {TITLE_LIMIT}.")
    if len(highlights) > HIGHLIGHTS_LIMIT:
        errors.append(
            f"Item Highlights has {len(highlights)} characters; limit is {HIGHLIGHTS_LIMIT}."
        )
    if "|" in title or "|" in highlights:
        errors.append("Do not put the report delimiter '|' into either Seller Central field.")

    found_prohibited = sorted(PROHIBITED_TITLE_CHARACTERS.intersection(title))
    if found_prohibited:
        errors.append(
            "Title contains prohibited character(s): " + ", ".join(found_prohibited)
        )

    combined_casefold = f"{title} {highlights}".casefold()
    found_promotional = [
        phrase for phrase in HARD_PROMOTIONAL_PHRASES if phrase in combined_casefold
    ]
    if found_promotional:
        errors.append(
            "Promotional phrase(s) found: " + ", ".join(sorted(set(found_promotional)))
        )

    found_subjective = [
        phrase
        for phrase in SUBJECTIVE_PHRASES
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", combined_casefold)
    ]
    if found_subjective:
        warnings.append(
            "Review subjective phrase(s): " + ", ".join(sorted(set(found_subjective)))
        )

    title_counts = Counter(token for token in words(title) if token not in STOPWORDS)
    repeated = sorted(token for token, count in title_counts.items() if count > 2)
    if repeated:
        errors.append("Title repeats word(s) more than twice: " + ", ".join(repeated))

    relations = cross_field_relations(title, highlights)
    redundant_overlaps = sorted(
        {
            relation["title_term"]
            for relation in relations
            if relation["type"] == "redundant_exact"
        }
    )
    if redundant_overlaps:
        warnings.append(
            "Review redundant cross-field exact overlap: "
            + ", ".join(redundant_overlaps)
        )
    semantic_overlaps = sorted(
        {
            f'{relation["title_term"]} ~ {relation["item_highlights_term"]}'
            for relation in relations
            if relation["type"] == "semantic_overlap_review"
        }
    )
    if semantic_overlaps:
        warnings.append(
            "Review cross-field semantic overlap or adjective-only refinement: "
            + ", ".join(semantic_overlaps)
        )

    if highlights and not re.search(r"[,;，；、]", highlights) and len(highlights) > 40:
        warnings.append("Item Highlights should use comma-separated phrases.")
    if highlights.endswith((".", "!", "?", "。", "！", "？")):
        warnings.append("Item Highlights should be phrases, not a complete sentence.")

    missing_unit_spaces = sorted(
        set(
            match.group(0)
            for match in re.finditer(
                r"(?<!\d)\d+(?:[.,]\d+)?(?:kg|g|cm|mm|ml|oz|in)\b",
                combined_casefold,
            )
        )
    )
    if missing_unit_spaces:
        warnings.append(
            "Review spacing between values and units: " + ", ".join(missing_unit_spaces)
        )

    return {
        "valid": not errors,
        "marketplace": marketplace.upper(),
        "title": title,
        "title_characters": len(title),
        "title_limit": TITLE_LIMIT,
        "item_highlights": highlights,
        "item_highlights_characters": len(highlights),
        "item_highlights_limit": HIGHLIGHTS_LIMIT,
        "errors": errors,
        "warnings": warnings,
        "cross_field_relations": relations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--item-highlights", required=True)
    parser.add_argument("--marketplace", default="US")
    args = parser.parse_args()

    result = validate(args.title, args.item_highlights, args.marketplace)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
