# Amazon Search and Shopping-AI Evidence Boundaries

Use this reference for selecting and explaining July 2026 Title + Item Highlights candidates and for the evidence boundaries of Rufus/Alexa product Q/A. Use `rufus-qa-workflow.md` for the Q/A schema and generation procedure. This reference does not define an Amazon ranking formula.

Use `title-allocation-2026.md` for the v2 phrase schema and allocation procedure.

Sources checked on 2026-07-22:

- Amazon SEO seller guidance, published 2025-09-03: https://sell.amazon.com/blog/amazon-seo
- Seller Central search optimization: https://sellercentral.amazon.de/help/hub/reference/external/GNYWHX2TP7C8GXHK
- Amazon Science COSMO publication, 2024: https://www.amazon.science/publications/cosmo-a-large-scale-e-commerce-common-sense-knowledge-generation-and-serving-system-at-amazon
- Amazon Science Rufus technology article, 2024: https://www.amazon.science/blog/the-technology-behind-amazons-genai-powered-shopping-assistant-rufus
- Amazon announcement for Alexa for Shopping, 2026-05-13: https://www.aboutamazon.com/news/retail/alexa-for-shopping-ai-assistant

## Amazon SEO and the A9 label

Amazon's seller guidance supports these actions:

- Research the words and phrases customers use for relevant products.
- Put the most important, relevant product details and primary terms in the title naturally.
- Use secondary terms in other listing fields rather than stuffing the title.
- Use customer search data when available, including Brand Analytics and Product Opportunity Explorer.
- Write naturally; keyword stuffing can create a poor customer experience and hurt performance.

The Amazon SEO page checked above does not publish ranking weights or a formula. Treat `A9` as a seller-industry shorthand for traditional Amazon SEO and lexical relevance, not as a verified name for one current unified algorithm. Do not claim an `A9 score`, exact field weight, guaranteed position, or direct causal ranking lift.

The 2025 Amazon SEO page contains an older title-length statement. For July 2026 Title + Item Highlights, the 2026 policy in `amazon-title-policy-2026.md` supersedes that length guidance.

## COSMO

Amazon Science describes COSMO as a system that mines user-centric e-commerce commonsense knowledge from behavior and constructs knowledge graphs. It has been deployed in Amazon search applications such as search navigation and is intended to help bridge semantic gaps between queries, products, and user intentions.

Conservative listing implication:

- Include factual purposes, scenarios, audiences, compatibility, and problems solved when they help shoppers distinguish the product.
- Put secondary intent and use-case information in Item Highlights when the Title is already complete.
- Never infer a product attribute merely because an intent is plausible.

COSMO does not publish seller-copy weights and does not prove that inserting a use-case phrase produces a specific ranking gain.

## Rufus / Alexa for Shopping

Amazon Science states that Rufus uses reliable sources such as the product catalogue, customer reviews, and community questions and answers to answer product-detail, comparison, and recommendation questions. Amazon announced the shopping assistant under the current `Alexa for Shopping` name on 2026-05-13; keep `Rufus` as the familiar historical name when explaining the framework.

Conservative listing implication:

- State product type, material, dimensions, capacity, compatibility, care, included items, quantified performance, and use cases explicitly when supported by product facts.
- Prefer direct factual phrases that can answer questions such as material, fit, washability, or intended use.
- Do not quote or invent reviews, community answers, certifications, performance tests, or comparative superiority.

Rufus/Alexa for Shopping is not a disclosed seller-ranking formula. Do not promise that a phrase will cause recommendation, citation, or ranking.

## Candidate-selection rule

Use evidence in this order:

1. User-provided product facts and keyword data.
2. Current Amazon policy.
3. Amazon first-party search data or directly observed listing data.
4. Conservative intent and answerability principles from Amazon Science.

When evidence is missing, omit the claim and state the limitation in Chinese diagnostics.

## Internal field-allocation method

This method combines the public evidence boundaries above with the July 2026 field limits. It is a skill heuristic, not a disclosed A9, COSMO, Rufus, or Alexa weighting model.

Use the exact optimized legacy title as the sole reference title. Decompose it into ordered semantic phrases, then build a verified fact pool from the original product facts, keyword evidence, selling-point evidence and variants. Generated legacy copy is a wording reference, not independent proof. Evaluate the Title and Item Highlights together: a secondary search intent belongs in the pair only when a direct product fact supports it and the target-language expression remains natural.

Evaluate each phrase through these questions:

1. **Product identity**: Does it answer what the product is? Verified brand and the natural core product phrase belong in the Title.
2. **Dual-value differentiation**: Is the same verified attribute supported by keyword, selling-point, and differentiation evidence? Give it Title priority immediately after identity.
3. **Variation identity**: Is it a necessary child size, color, model, or capacity? Evaluate the complete set only after reserving space for higher-priority dual-value differentiators.
4. **Other dual value**: Is the verified phrase supported by both keyword and selling-point evidence without separate differentiation evidence?
5. **Hard fact or differentiation**: Does it express a verified specification or a product-specific distinction without an unsupported claim?
6. **Keyword evidence**: Is the wording supported by user data, Amazon first-party data, or directly observed relevant listings and also compatible with verified product facts?
7. **Purchase-decision value**: Does it resolve an important shopper decision such as material, installation, fit, compatibility, or supported use?
8. **Character efficiency and language quality**: How much verified information does it add for its character cost, and does the pair remain natural in the marketplace language?
9. **Legacy continuity**: Can the original phrase and relative order be retained without harming compliance, clarity, or grammar?

Use this internal priority order:

`identity → dual_value_differentiator → SKU → dual_value → verified specification or differentiator → keyword_only → selling_point_only → secondary`

Brand and the core product/category phrase are the first component requirements. A phrase with direct fact, keyword, selling-point, and differentiation references has priority over applicable child SKU attributes. Evaluate SKU placement after retaining such phrases. A generic differentiator remains optional and has no universal fixed position. Competitor wording and keyword data may prioritize or validate relevance, but they may not create an unsupported product claim.

At the same priority, compare legacy phrase reuse, keyword data, purchase-decision value, character efficiency, language naturalness, then legacy relative order. Do not set a fixed reuse ratio. Record each phrase allocation and every controlled rewrite or omission reason so the selection remains auditable.

New candidate wording must have direct fact evidence. Do not infer `kratzfest`, `stabil`, load capacity, compatibility, certification, audience, or another attribute merely because it is plausible for the category. For child ASINs, move the complete SKU set to Item Highlights when adding it after higher-priority dual-value differentiators would make the Title exceed 75 characters.

After satisfying identity and SKU placement, allocate remaining phrases contextually rather than permanently assigning attribute types to fields. A compact care term may earn a place in one product's Title but move to Item Highlights in another product when the fuller care phrase is more useful there. Record every high-priority fact in a pair-coverage audit; do not omit a fact merely because the Title has already reached a natural length when the 125-character Highlights field can express it.

### Controlled cross-field refinement

Cross-field reuse is useful only when the second field adds concrete, supported information:

- Summary-to-quantity: `Ventose` → `4 ventose potenti`.
- Summary-to-performance: `Saugnäpfe` → `4 starke Saugnäpfe bis 18 kg`.
- Exact restatement: `waschbar` → `waschbar` is redundant and must be rewritten.
- Generic-to-specific waste: `Kunstfell` + `Kunstkaninchenfell` should normally be reduced to the specific term.

An added adjective alone is not proof of useful refinement. Require a verified count, measurement, specification, structure, compatibility, use, or other concrete fact. Record the reason for every retained refinement in Chinese `deduplication_notes`.

The repeated-word policy is evaluated within the Title. Do not invent a cross-field frequency limit, and do not assume that reuse gives equal search weight in both fields.
