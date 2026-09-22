---
name: kjxj-amzai-make-jdmx
description: Analyze an Amazon competitor product URL or an ASIN with its marketplace, and extract 5-8 target-market keywords plus a 50-80-word concise product description for AI product-detail generation. Use when a seller needs an evidence-based competitor product summary in the language and terminology of the competitor marketplace.
---

# Amazon Competitor Keywords and Description

Produce a compact, evidence-based keyword set and product description. Do not rewrite the competitor listing, create a full listing, or add unverified selling points.

## Input

Accept either:

- A full Amazon product URL, including its marketplace domain.
- An ASIN plus the target marketplace, for example `B0GD7M884P, Amazon.de`.

For an ASIN-only request without a marketplace, ask for the intended Amazon marketplace. An ASIN alone does not reliably determine a country store. Normalize URLs to `/dp/<ASIN>` while retaining the supplied marketplace domain.

## Retrieval

1. Retrieve the product page directly. Prefer a suitable structured connector or page-retrieval tool; otherwise use Browser, then Chrome, then a public product-page fallback.
2. Verify the title, breadcrumb category, selected variation, and visible product bullets. Capture product type, materials, closure or mechanism, dimensions or capacity when visible, care instructions, compatible content, target users, and use scenarios.
3. Preserve only facts visible on the product page. Never infer material, waterproofing, safety, certifications, included accessories, medical effects, environmental claims, or performance claims.
4. If essential fields cannot be retrieved, use only the verified subset. State the missing fields briefly in Chinese before the required output; do not fill gaps by assumption.

## Extraction Rules

- Identify the core category, primary function, and 2-3 distinguishing verified features.
- Select 5-8 high-relevance keywords from the product type, material, use, mechanism, feature, and audience. Use common terminology for the product's marketplace and avoid brands, prices, ratings, duplicate terms, and unsupported search terms.
- Write the description in the marketplace listing language. Use the predominant language of the product content rather than the browser interface language.
- Keep the description to 50-80 words, one paragraph, and include the product type, 2-3 core selling points, and main use scenarios.
- Keep wording factual and information-dense. Avoid superlatives, reviews, rankings, discounts, guarantees, and promotional calls to action.
- Do not claim a feature merely because it appears in a comparison product, related-product carousel, customer question, or search suggestion.

## Required Output

Return only the following copy-ready format. Use ASCII commas between keywords.

```text
【关键词】:keyword 1,keyword 2,keyword 3,keyword 4,keyword 5
【简短描述】:One 50-80-word paragraph in the marketplace language.
```
