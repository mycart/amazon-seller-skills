# Amazon Search and Shopping-AI Evidence Boundaries

Use this reference only for selecting and explaining July 2026 Title + Item Highlights candidates. It does not define an Amazon ranking formula.

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

For each verified fact, evaluate:

1. **Product identity**: Does it answer what the product is? Brand and the natural core product phrase belong in the Title.
2. **Fit and compatibility**: Does it decide whether the product fits or works, such as dimensions, capacity, model, or compatible device?
3. **Category-specific first-screen decision**: Does the category make installation method, connector, operating format, or another attribute an early shopper check?
4. **Differentiation**: Does the fact distinguish this product from close alternatives without an unsupported claim?
5. **Keyword evidence**: Is the wording supported by user data, Amazon first-party data, or directly observed relevant listings?
6. **Character efficiency**: How much verified decision information does the phrase add for its character cost?
7. **Language quality**: Does the complete Title remain natural and independently understandable in the marketplace language?

Use the answers to allocate facts rather than permanently assigning attribute types to fields. A compact care term may earn a place in one product's Title but move to Item Highlights in another product when the fuller care phrase is more useful there. A high-importance load specification may also move to Item Highlights when its character cost would crowd out identity, fit, or a category-critical cue.

### Controlled cross-field refinement

Cross-field reuse is useful only when the second field adds concrete, supported information:

- Summary-to-quantity: `Ventose` → `4 ventose potenti`.
- Summary-to-performance: `Saugnäpfe` → `4 starke Saugnäpfe bis 18 kg`.
- Exact restatement: `waschbar` → `waschbar` is redundant and must be rewritten.
- Generic-to-specific waste: `Kunstfell` + `Kunstkaninchenfell` should normally be reduced to the specific term.

An added adjective alone is not proof of useful refinement. Require a verified count, measurement, specification, structure, compatibility, use, or other concrete fact. Record the reason for every retained refinement in Chinese `deduplication_notes`.

The repeated-word policy is evaluated within the Title. Do not invent a cross-field frequency limit, and do not assume that reuse gives equal search weight in both fields.
