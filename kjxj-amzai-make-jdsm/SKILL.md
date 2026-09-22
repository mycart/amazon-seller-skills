---
name: kjxj-amzai-make-jdsm
description: Analyze an Amazon competitor product URL or an ASIN with its marketplace, then produce a 100-150-word custom instruction for AI product-detail creation. Use when a seller needs to convert a competitor listing's bullets, value proposition, target customer, and usage scenarios into an evidence-based creation brief in the competitor marketplace's language.
---

# Amazon Competitor Detail Brief

Create one concise, evidence-based instruction for generating a product detail page. The deliverable is not a rewritten competitor listing.

## Input

Accept either:

- A full Amazon product URL, including any marketplace domain.
- An ASIN plus the target marketplace, for example `B0GD7M884P, Amazon.de`.

For an ASIN-only request that does not identify a marketplace, ask which Amazon marketplace to use; an ASIN does not reliably identify one. Normalize a supplied URL to its `/dp/<ASIN>` product page and retain the marketplace domain.

## Research Workflow

1. Retrieve the public product page with a suitable structured web/page retrieval tool. Use the known product URL directly. If the response is incomplete, retry with an appropriate browser or retrieval method; do not invent unavailable page content.
2. Capture the product title, category, visible bullet points, product description, material/care claims, and any visible safety, certification, age, compatibility, or regulatory information.
3. Analyze the first five substantive bullets as the primary structure. Identify each bullet's customer benefit, feature proof, and scenario. Treat extra bullets separately; do not call them part of a five-bullet structure.
4. Derive the unique value proposition, target users, pain points, and use cases only from the captured evidence. Separate direct claims from reasonable editorial guidance. Do not infer certifications, safety performance, sustainability, medical effects, or legal compliance.

## Writing Rules

- Write the final instruction in the language used by the target marketplace listing. Do not let a scraper's translated interface change that choice. For example, use German for a German-language Amazon.de listing.
- Produce exactly one paragraph of 100-150 words, excluding the heading. Count words according to the target language's normal space-delimited word convention.
- Organize the paragraph as an instruction to another AI. It must state: 3-4 core advantages to foreground; the differentiating feature; target customer pain points and scenarios; the intended tone; and compliance guidance.
- Prefer benefit-led sequencing: product form and access/use benefit, differentiating mechanism, durability or care proof, then audience and scenarios.
- Mention compliance only when supported by the page. Otherwise instruct the downstream AI to use only verified material, performance, care, safety, certification, environmental, and regulatory claims for the target market.
- Avoid brand names, price, ratings, review claims, keyword stuffing, superlatives, and competitor-copy phrasing unless the user explicitly asks for them.

## Required Output

Return only this format, with no analysis preface, bullets, citations, or translation:

```text
【自定义说明】:
(one 100-150-word paragraph in the competitor listing language)
```
