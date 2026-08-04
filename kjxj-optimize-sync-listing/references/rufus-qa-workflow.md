# Rufus / Alexa for Shopping Q/A Workflow

Use this reference after the normal listing workflow when producing reusable Q/A content for Premium A+ pages. Treat Rufus as the familiar historical name; Amazon currently calls the shopping assistant Alexa for Shopping. This workflow improves factual answerability only. It is not an Amazon ranking formula and must not promise recommendation, citation, or ranking gains.

## Evidence order

Use current, attributable evidence in this order:

1. User-provided product facts, product documents, and seller data.
2. The verified main-ASIN product page and Amazon catalogue fields for the target marketplace.
3. User keyword files and Amazon first-party search data for wording and intent, not for inventing product attributes.
4. Current Amazon Community Q&A, recent visible reviews, and verified competitor pages or reviews for shopper concerns. These sources may determine what to ask, but they may not create a fact about the seller's product.
5. Amazon first-party science or policy sources for methodology only.

For web evidence, record the URL, marketplace, retrieval timestamp, and the exact verified facts used. Prefer repeated concern themes supported by at least two visible observations. A single review may identify a low-confidence question but cannot substantiate a product claim. Never invent unavailable page fields, reviews, tests, certificates, guarantees, or comparative superiority.

## Product scope

Create one Q/A set for the main ASIN or product family. Keep answers variation-neutral unless a color, size, model, or compatibility fact applies to every included variation. Do not mention competitor brands or ASINs in paste-ready Q/A copy unless the user explicitly requests a factual comparison.

## Twelve-question allocation

For a complete set, generate exactly 12 unique Q/A items using these topic codes:

| Topic code | Count | Coverage |
|---|---:|---|
| `product_identity` | 2 | Product name, category, selection or fit identity |
| `feature_material` | 3 | Core function, material, construction, verified differentiators |
| `audience_use_case` | 2 | Audience, scenario, compatibility, intended use |
| `buyer_concern` | 3 | Verified shopper concerns, care, durability, installation, purchase objections |
| `setup_care_included` | 2 | Setup, operation, maintenance, included items |

Write each question in natural shopper language and each answer as concise, factual marketplace-language copy. Distribute supported semantic terms naturally across the set; never create keyword-collage questions. Every item must contain at least one semantic keyword and reference at least one direct product-fact source (`user`, `product_document`, `seller_data`, or `amazon_product`). Review, competitor, keyword, and research sources can supplement but cannot replace direct product evidence.

If verified facts cannot support 12 distinct answers after reasonable evidence retrieval, return only the supported subset with `status: evidence_insufficient`, keep `target_count: 12`, and add Chinese limitations explaining the missing coverage. Never pad the list with generic advice, placeholders, or unsupported claims.

## Report interface

Store the result in the listing report under `rufus_qa`:

```json
{
  "status": "complete",
  "target_count": 12,
  "marketplace": "DE",
  "language": "de_DE",
  "items": [
    {
      "id": "QA-01",
      "topic": "product_identity",
      "question": "Marketplace-language question",
      "answer": "Marketplace-language answer",
      "question_zh": "中文问题翻译，仅用于审核",
      "answer_zh": "中文答案翻译，仅用于审核",
      "semantic_keywords": ["supported term"],
      "evidence_refs": ["E-01"]
    }
  ],
  "evidence": [
    {
      "id": "E-01",
      "source_type": "amazon_product",
      "source_title": "Original source title",
      "source_url": "https://...",
      "retrieved_at": "2026-07-29T10:00:00+00:00",
      "marketplace": "DE",
      "verified_facts": ["中文事实说明"],
      "used_by": ["QA-01"]
    }
  ],
  "limitations": []
}
```

Validate the completed object and create its Markdown artifact with:

```bash
<skill>/scripts/validate-rufus-qa.py --input "<qa-or-report-json>" --output "<validation-json>" --markdown "<rufus-qa-md>"
```
