# July 2026 Title Semantic Allocation v4

Use this reference after the legacy Listing is complete and before generating the three
July 2026 Title + Item Highlights options. Read `amazon-title-policy-2026.md` for hard
Amazon rules and `search-ai-evidence.md` for evidence boundaries.

## Contents

1. Evidence boundary
2. Reference-title decomposition
3. Priority and title-budget allocation
4. Semantic groups and controlled rewriting
5. v4 report contract
6. Validation rules
7. Generalized case matrix
8. Quality-generation protocol
9. Scoring and tie breaks

## 1. Evidence boundary

- Use `legacy_generation.legacy_listing.title` as the sole wording reference for legacy-derived phrases. The only allowed identity override is the selected user core traffic keyword defined below.
- Use user facts, verified optimized-ASIN Listing fields, variant data, and other reliable
  product evidence as the factual boundary. Generated legacy wording alone is not evidence.
- Keyword and competitor data may establish search relevance or ordering. They may not prove
  that the optimized product has an attribute or that an attribute is unique in the market.
- Do not add stability, durability, comfort, load, certification, compatibility, audience, or
  performance claims from category plausibility.
- Treat the examples in this file as decomposition patterns, not reusable product evidence.

## 2. Reference-title decomposition and fact pool

Split the legacy title into the smallest useful ordered semantic phrases. Preserve exact
`source_text`, but do not split a meaningful phrase so finely that it loses its intent.

Supported roles include:

- Identity: `brand`, `core_product`, `category_synonym`.
- Intent and variation: `intent_modifier`, `shape`, `capacity`, `sku_attribute`.
- Facts: `material`, `installation`, `specification`, `quantity`, `compatibility`,
  `structure`, `included_accessory`, `performance`.
- Benefits and context: `function`, `benefit`, `care`, `audience`, `use_case`, `style`.

Use `semantic_group_id` to connect a primary category phrase to its synonyms, functional
aliases, and refinements. A Title may contain only one `primary`, `synonym`, or
`functional_alias` member of the same group. A `refinement` may coexist when it adds a
different verified decision detail.

Build `title_pair_fact_pool` after decomposition. It may include verified information from
the current product page, user facts, variants and keyword material that is not present in the
legacy title. Every item requires `id`, `text`, direct `fact_refs`, optional `keyword_refs` and
`selling_point_refs`, `decision_factor`, `decision_value`, and literal `character_cost`.
The legacy title is a wording source only: it never upgrades an unsupported claim to a fact.

## 3. Priority and title-budget allocation

### Core traffic keyword selection

Evaluate all user-provided core keywords before allocating legacy phrases. For each candidate,
record its original input order and require all of the following:

- It is written in the target marketplace language.
- Direct product facts confirm that the complete phrase identifies the product category.
- The unified keyword pool marks it `listing_eligible: true`.
- It has either a positive real `search_volume`, `monthly_search_volume`, `impressions`,
  `clicks`, or `search_frequency` metric from user/file/SellerSprite evidence, or the user
  explicitly identifies it as a traffic word.

Select the first eligible phrase in user input order. A later phrase with a higher metric may
not replace it. Use the selected phrase as `title_components.core_product_phrase` in all three
options. Preserve every word and its order as one contiguous phrase; permit only Unicode, case,
whitespace, and punctuation normalization. Do not delete, substitute, reorder, or inflect words.

When the selected phrase is absent from the legacy title, add it through
`additional_verified_phrases` with direct category fact and keyword references. The legacy
category phrase remains decomposed and auditable, but may be omitted as a redundant member of
the same semantic group. If Brand plus the complete selected phrase cannot pass the 75-character
or policy gate, block the options and record a Chinese reason rather than shortening the phrase.

Apply this order:

1. Brand and the complete selected core traffic keyword, or the verified legacy core category phrase when no user keyword qualifies.
2. `dual_value_differentiator` phrases.
3. Complete necessary child SKU attribute set.
4. Other `dual_value` phrases.
5. Verified hard specifications or differentiating attributes.
6. Keyword-only phrases.
7. Selling-point-only phrases.
8. Secondary scenario, care, audience, and style information.

Classify a phrase as `dual_value_differentiator` only when all four lists are non-empty:

- `fact_refs`: direct proof that the optimized product has the attribute.
- `keyword_refs`: product-keyword evidence for the phrase or controlled equivalent.
- `selling_point_refs`: evidence that the phrase is an intended product selling point.
- `differentiation_refs`: user or verified product evidence identifying it as an important
  differentiating purchase attribute.

This classification means the attribute is important and differentiated for this product
positioning. It does not claim market exclusivity.

Assign every `dual_value_differentiator` a unique contiguous `dual_value_rank`, starting at 1.
Rank multiple phrases by keyword data, purchase-decision value, useful legacy wording reuse,
character efficiency, marketplace-language naturalness, then legacy source order.

For every candidate:

1. Build the shortest natural Brand + Core Product identity.
2. Add ranked `dual_value_differentiator` phrases before considering SKU attributes.
3. Create `sku_fit_evaluation.priority_base_title` from that higher-priority content.
4. Add the complete SKU set to the evaluation string.
5. Keep the complete SKU set in Title when the evaluated result is at most 75 characters.
6. Otherwise retain the higher-priority phrase and move the complete SKU set to Item
   Highlights. Never split the set.
7. Only after this decision, allocate lower-priority optional phrases.

Evaluate each dual-value differentiator in rank order. Build its `title_fit_evaluation.base_title`
from Brand + Core Product plus any higher-ranked dual-value differentiators already retained in
Title. Exclude SKU and every lower-priority phrase from this base. If the phrase cannot fit after
its shortest natural controlled rewrite, it may move or be omitted only for `character_limit`,
`policy`, `evidence_conflict`, `redundancy`, or `language_quality`. A phrase that fits may not use
`character_limit` as its reason. After an allowed move or omission, continue with the next ranked
dual-value differentiator and then recalculate SKU fit from the higher-priority phrases actually
retained in Title.

## 4. Semantic groups and controlled rewriting

Allowed semantic operations:

- `normalize_case`, `normalize_punctuation`, `compact_unit`, `inflect`, `reorder`.
- `retain_anchor`: keep the decisive anchor from a longer reference phrase.
- `drop_redundant_category`: remove a secondary category synonym while keeping its modifier.
- `add_role_label`: add a neutral label such as `Material` or `Design` without creating a new
  product property.
- `expand_supported_detail`: add a verified quantity, specification, structure,
  compatibility, or use.

Use these realization types:

- `verbatim`: exact source text; no rewrite operations or added tokens.
- `normalized`: same evidence-bearing tokens with controlled case, punctuation, inflection,
  or unit presentation.
- `controlled_rewrite`: may drop, reorder, or inflect source content but may not introduce an
  unrelated content word.
- `supported_refinement`: may introduce content tokens only when `added_tokens` exactly lists
  them and direct `fact_refs` support them.

One reference phrase may have one realization in each field. Cross-field reuse is valid only
when Item Highlights add verified information. Examples:

- Title `Velcro`; highlights `Self-adhesive Velcro base`.
- Title `Ventouses`; highlights `4 ventouses, supporte jusqu'à 18 kg` when both details are
  directly supported.
- Title `waschbar`; highlights `waschbar` is an invalid exact restatement.

## 5. v4 report contract

Set:

```json
{
  "title_options_generation": {
    "reference_title": "Exact legacy optimized title",
    "method": "legacy_reference_phrase_allocation_v4",
    "core_keyword_selection": {
      "status": "selected",
      "selection_rule": "first_eligible_user_input",
      "preservation_mode": "all_tokens_same_order_normalization_only",
      "selected_keyword": "Portable Blender",
      "reason": "按用户输入顺序选择第一个符合品类且有流量证据的核心关键词",
      "candidates": [
        {
          "keyword": "Portable Blender",
          "input_order": 1,
          "marketplace_language_match": true,
          "category_match": true,
          "category_fact_refs": ["FACT-PRODUCT-TYPE"],
          "listing_eligible": true,
          "traffic_status": "verified_metric",
          "traffic_evidence": [
            {"type": "metric", "source": "user_keyword_file", "metric": "search_volume", "value": 45000}
          ],
          "eligible": true,
          "reason": "该词符合商品品类、目标语言和流量词要求"
        }
      ]
    },
    "reference_phrase_analysis": [],
    "title_pair_fact_pool": [
      {
        "id": "TPF-01",
        "text": "Self-adhesive Velcro base",
        "fact_refs": ["FACT-VELCRO"],
        "keyword_refs": ["KW-SELF-ADHESIVE"],
        "selling_point_refs": ["SP-INSTALLATION"],
        "decision_factor": "installation",
        "decision_value": "high",
        "character_cost": 26
      }
    ]
  }
}
```

Each `reference_phrase_analysis` item contains the existing v1 fields plus:

```json
{
  "differentiation_refs": ["DIFF-01"],
  "decision_factor": "installation",
  "decision_value": "high",
  "decision_reason": "该安装方式同时影响搜索意图和购买判断",
  "semantic_group_id": "SG-01",
  "semantic_relation": "primary",
  "dual_value_rank": 1
}
```

Use `semantic_relation: none`, an empty `semantic_group_id`, and `dual_value_rank: 0` when the
fields do not apply. Decision values are `required`, `high`, `medium`, and `low`.

Each v4 allocation contains:

```json
{
  "phrase_id": "RP-03",
  "status": "used",
  "reason_code": "retained",
  "reason": "该词兼具关键词、卖点和差异化属性价值，优先进入标题",
  "realizations": [
    {
      "placement": "title",
      "text": "Velcro",
      "reuse_type": "controlled_rewrite",
      "rewrite_operations": ["retain_anchor"],
      "added_tokens": [],
      "fact_refs": ["FACT-VELCRO"],
      "reason": "标题保留固定方式核心词"
    },
    {
      "placement": "item_highlights",
      "text": "Self-adhesive Velcro base",
      "reuse_type": "verbatim",
      "rewrite_operations": [],
      "added_tokens": [],
      "fact_refs": ["FACT-VELCRO"],
      "reason": "亮点补充自粘底座结构"
    }
  ]
}
```

Each option also contains a complete `title_pair_coverage_audit`. Use `omitted` only with an
allowed omission reason; high-priority verified facts must be allocated whenever they fit in the
two-field budget.

For every high-priority non-identity fact, add `highlight_candidate` to the fact-pool entry.
It contains the most complete natural Item Highlights expression, its direct `fact_refs`, literal
`character_cost`, and a Chinese `title_information_gain` explaining the structural, measured,
compatibility, care, or use detail it adds beyond a shorter Title expression. This permits a
Title anchor such as `Klettband` while preserving a directly evidenced complementary phrase in
Item Highlights. Do not create a candidate from a generic adjective or a fact not directly
proved for the current product.

```json
[
  {
    "fact_id": "TPF-01",
    "placement": "item_highlights",
    "text": "Self-adhesive Velcro base",
    "reason": "商品亮点补充安装结构，避免只重复标题中的 Velcro"
  }
]
```

An omitted allocation uses `status: omitted`, an empty `realizations` array, an allowed
omission reason code, and a Chinese reason.

When a dual-value differentiator is not in Title, also provide:

```json
{
  "title_fit_evaluation": {
      "base_title": "Brand Core Product Higher Ranked Differentiator",
    "evaluated_text": "Shortest natural differentiator wording",
    "combined_characters": 81,
    "fits": false,
    "reason": "品牌、核心品类和该双重差异化词组合后超过75字符"
  }
}
```

Every option contains:

```json
{
  "sku_fit_evaluation": {
    "priority_base_title": "Brand Core Product Higher Priority Phrase",
    "sku_attributes": ["White", "60 x 40 cm"],
    "base_characters": 47,
    "with_sku_characters": 68,
    "limit": 75,
    "fits": true,
    "final_placement": "title",
    "reason": "先保留品牌、品类和双重差异化词，再评估完整SKU属性组"
  }
}
```

Keep `additional_verified_phrases` for content not derived from the reference title. Every
item still requires direct `fact_refs` and a Chinese reason.

## 6. Validation rules

- Fully and uniquely decompose every evidence-bearing reference-title token in source order.
- Require the v4 core-keyword selection object and validate candidate evidence, input order, eligibility, and the selected phrase.
- Require v4 decision, semantic, and differentiation fields on every phrase.
- Derive priority deterministically from roles and evidence references.
- Require contiguous `dual_value_rank` values.
- Require every candidate token to be covered by v4 realizations or verified additions.
- Require every option to contain the complete selected core keyword as one contiguous ordered phrase.
- Reject unsupported refinement tokens or fact-free additions.
- Reject multiple primary/synonym/functional-alias members of one semantic group in Title.
- Reject cross-field reuse when Item Highlights add no information.
- Validate every omitted differentiator against Brand + Core Product + retained higher-ranked
  differentiators, with SKU and lower-priority content excluded from the fit base.
- Validate SKU fit against the higher-priority base title after allowed differentiator moves,
  not against a title that removed a differentiator merely to preserve SKU.
- Keep Title at 75 characters and Item Highlights at 125 characters or fewer.
- Add `highlight_capacity` to every option. It must list usable fact-pool candidate IDs, their
  reproducible total character capacity, the dynamic target, actual Item Highlights length,
  capacity status, and a Chinese allowed-reason entry for every usable candidate not allocated.
- When at least three usable complementary candidates have 100 or more combined characters,
  Item Highlights must reach 100 characters unless a policy, redundancy, language-quality, or
  character-limit exception is individually documented. For lower evidence capacity, target the
  complete usable candidate set rather than padding toward 125 characters.
- Titles at 74 or 75 characters pass with a headroom warning and lose a small amount of
  `mobile_clarity` in internal scoring.
- Normalize to Unicode NFC before counting. Do not count UTF-8 bytes.
- Accept compact multidimensional sizes such as `120x50x66cm` without a spacing warning.

## 7. Generalized case matrix

### Hidden litter-box cabinet, German

- Core identity: `Katzenklo Schrank`.
- Intent modifier: `verstecktes` may move next to the core phrase when evidence supports its
  keyword, selling-point, and differentiation value.
- High decision facts: `für 2 Katzen`, furniture dimensions, and child color.
- Secondary facts: MDF, litter mat, magnetic double doors, and cabinet style.
- `MDF-Material` and `modernes Kommoden-Design` are supported role-label rewrites.
- `robust und stabil` requires separate direct evidence.
- Boundary pair: 72-character Title and 101-character Item Highlights.

### Heart-shaped snuffle mat, US

- Core identity: `Snuffle Mat for Dogs`.
- Shape modifier: `Heart Shaped` may be promoted near the core phrase.
- `Velcro` may remain in Title while `Self-adhesive Velcro base` supplies the full structural
  detail in Item Highlights.
- `Slow Feeder Puzzle Toy` is a functional alias and belongs outside the Title when the core
  category already identifies the product.
- `promotes slower eating` requires direct product evidence; `fun and engaging` is subjective
  and unsupported unless reliable evidence justifies a compliant expression.
- Boundary pair: 71-character Title and 119-character Item Highlights.

### Dog bed, German

- Keep one primary category anchor: `Hundebett`.
- Group `Hundekorb` and `Hundesofa` as category synonyms.
- Retain the shape from `rechteckiges Hundesofa` as `rechteckiges Design` only with the
  controlled role-label audit.
- Size, material, washability, and child color compete by evidence and decision value after
  higher-priority dual-value differentiators.
- `pflegeleicht`, `weich`, and `bequem` require direct evidence beyond category or material
  plausibility.
- Boundary pair: 67-character Title and 108-character Item Highlights.

### Window cat hammock, French

- Core identity: `Hamac Chat Fenêtre`.
- Installation phrase `à Ventouses` may receive dual-value-differentiator priority when all
  four evidence lists are present.
- Split `Fausse Fourrure Effet Lapin` into material summary and supported refinement.
- Keep foldability, verified load, removable/washable cover, and other secondary details in
  Item Highlights as space requires.
- `doux et confortable` and `fixation stable` require direct evidence.
- Boundary pair: 75-character Title and 110-character Item Highlights. The Title is valid but
  must receive the headroom warning.

## 8. Quality-generation protocol

This is an internal copy-quality protocol, not an Amazon algorithm, field-weight model, or
performance prediction. Apply it to every new v4 report. It exists to make the three options
real alternatives rather than three labels attached to the same text.

### Candidate strategies

Generate exactly one option for each `generation_strategy`, in this order:

1. `search_identity`: Brand + the complete selected core traffic keyword + the most character-efficient verified differentiator.
2. `purchase_decision`: Brand + the complete selected core traffic keyword + the most decision-relevant verified material, structure, installation, specification, or compatibility fact.
3. `use_context`: Brand + the complete selected core traffic keyword + a verified use, care, audience, installation environment, or compatibility context.

Each strategy must use a distinct, directly evidenced focus phrase or focus detail in its Title
or Item Highlights. Do not count a score-only change, punctuation, capitalization, word-order
change, unit spacing, or a synonym with no additional verified detail as a different candidate.
When a named strategy has no directly evidenced applicable fact, use the next strongest unused
verified decision fact, record it as `fallback_verified_fact`, and explain the factual gap in
Chinese. Never invent a use case merely to fill the third option.

### Writing and allocation standard

- Write the Title as a natural marketplace-language noun phrase, never as a keyword string.
- Do not aim to fill 75 characters. Prefer 45-70 characters; use 71-75 only when the added
  wording is directly evidenced, high priority, and cannot provide equivalent decision value in
  Item Highlights.
- Write Item Highlights as 2-4 short, scannable fact phrases. Prefer a compact pattern such as
  `material or structure, installation or compatibility, care or measured specification` when
  the evidence supports it.
- Build Item Highlights in a second allocation pass after the Title is fixed. Add unused
  installation/structure, protection/compatibility, material/specification, care, and use facts
  in that order until the dynamic target, evidence boundary, or 125-character limit is reached.
- Each phrase must answer a distinct shopper question. Reuse a Title fact only when the
  Highlights phrase adds a verified measurement, quantity, structure, installation detail,
  compatibility, care instruction, or use context.
- Prefer the most concrete supported expression over generic adjectives. A claim such as
  `durable`, `strong`, `comfortable`, or `stable` still needs its own direct evidence.

### Required audit fields

Each option must include `generation_strategy`, `strategy_focus_phrase_ids`, a Chinese
`quality_rationale`, and non-empty `evidence_coverage`. `strategy_focus_phrase_ids` identifies
the reference phrase IDs that create the option's distinctive information. For a fallback, also
include `fallback_verified_fact` with direct fact references and a Chinese explanation.

Store the following internal 100-point assessment with every option. It is an audit aid only:

- `evidence_and_policy`: 35
- `identity_and_core_keyword`: 25
- `purchase_decision_information`: 15
- `natural_language_and_mobile_readability`: 15
- `cross_field_information_gain`: 10

Use a score of 0-100: evidence and policy 35, identity and variant completeness 20, pair
information coverage 20, keyword and search intent 15, natural language and mobile readability
10. Reject an option that
fails any hard policy, evidence, keyword-preservation, allocation, candidate-difference, or
cross-field information-gain rule before scoring it.

## 9. Scoring and tie breaks

Use the internal assessment defined above. This is not an Amazon algorithm score. Require each
option to include `title_pair_coverage_audit`, allocating every fact-pool item to Title,
Item Highlights, or an explained omission. When three or more high-priority non-identity facts
exist, Item Highlights must cover at least two distinct purchase-decision factors.

Rank the three valid candidates by total score. When candidates tie, prefer in this order:

1. Stronger direct evidence coverage.
2. Earlier and more natural complete core keyword.
3. Higher pair coverage of concrete purchase-decision facts.
4. Less redundant information across the two fields.
5. Shorter natural Title.

Do not claim A9, COSMO, Rufus, or Alexa field weights, guaranteed ranking effects, conversion
rates, or market uniqueness from this method.
