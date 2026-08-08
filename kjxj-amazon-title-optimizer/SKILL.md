---
name: kjxj-amazon-title-optimizer
description: >
  Optimize Amazon product titles into the "dual-field" structure (short Title
  under 75 characters plus Item Highlights under 125 characters) required by
  Amazon's title policy taking effect July 27, 2026. Use this skill whenever
  the user provides an Amazon product title (in any marketplace or language —
  DE, FR, IT, ES, NL, PL, SE, UK, US, etc.) and asks to optimize, shorten,
  restructure, or make it "new-rule compliant." Also trigger when the user
  mentions "双字段结构", "商品亮点", "Item Highlights", "75字符",
  "亚马逊标题新规", or pastes a long Amazon-style title without further
  instruction — a long pasted Amazon-style title is itself a signal this
  skill applies. Always produces the same structured output: a character-count
  diagnosis, the split-out Title, the split-out Highlights, a reasoning table
  for what stayed versus moved, a keyword-duplication check, and a compliance
  table.
---

# Amazon Dual-Field Title Optimizer

Splits an overlength Amazon product title into the new dual-field structure mandated by Amazon's July 27, 2026 title policy: a short **Title** (≤75 characters) plus **Item Highlights** (≤125 characters, comma-separated phrases). Works across any marketplace language (DE/FR/IT/ES/NL/PL/SE/UK/US/etc.) by applying the same prioritization logic regardless of language.

## Background facts (do not restate blindly — verify if the user questions currency)

- Amazon announced June 10, 2026 that titles will be capped at 75 characters (most categories, excluding books/media) effective **July 27, 2026**. A separate **Item Highlights** field (≤125 characters) will carry supplementary info, is itself searchable, and displays under the title on search results + detail pages.
- Item Highlights are written as **comma-separated short phrases**, not full sentences — maximize information density.
- After July 27, 2026, any title still over 75 characters gets auto-replaced by Amazon's AI-suggested version; sellers get a 14-day review window via "Manage Your Compliance" / listing quality dashboard to approve or edit.
- Separately, an **existing rule since Jan 21, 2025** (not part of the new rule, don't conflate) already prohibits: titles over 200 characters (legacy limit, being superseded), special/prohibited symbols, and **any word or phrase repeated more than 2 times** in a title (prepositions/articles/conjunctions excluded from the count).
- Underlying algorithm context (useful for prioritization, treat as background not gospel — sourced mainly from seller-community interpretation of Amazon's COSMO paper, not official marketing copy): A9 (literal keyword-matching, first-pass recall) + COSMO (semantic/intent re-ranking layered on top, launched ~March 2024) + Rufus (separate AI shopping-assistant discovery channel) operate as layered, co-existing systems — none of them replaced A9.
- If asked whether this policy is confirmed/still in effect, or for dates/details beyond what's here, use web_search — this is a fast-moving 2026 policy and the user may be checking on a date after this skill was written.

## Workflow

### Step 1 — Diagnose
Count the original title's characters (including spaces). State the count, how much it exceeds 75, and the overage percentage. Note if the title uses prohibited symbols (e.g. `|`, `*`, `!`, emoji) — flag these as a separate, already-in-effect violation, independent of the new rule.

### Step 2 — Classify every piece of information in the original title
Sort every element into one of two buckets using this priority order (highest priority survives into the 75-char Title first; everything else defaults to Highlights):

**Title-priority (roughly in this order, budget-permitting):**
1. Brand + core category noun (answers "what is this" — anchor for both A9 literal match and COSMO semantic match)
2. **Installation/mounting mechanism**, if the category has one and it's a binary purchase-decision fork (suction cups vs. no suction cups, wall-mount vs. floor, etc.) — treat this as equal priority to the category noun, not a minor detail
3. Hard numeric specs: size/dimensions, capacity ("for 2 cats"), weight capacity — these are usually the single highest-conversion-impact fact and should outrank vague descriptive equivalents (e.g. exact cm beats "small/medium dogs")
4. The core differentiating material/feature that drives CTR (e.g. faux rabbit fur, MDF) — keep the material itself, drop soft modifiers if space is tight, UNLESS dropping the modifier creates a factual-accuracy problem (see Step 4)
5. Color — cheap in characters, include if space allows; first thing to cut if the title is running over

**Highlights-bucket (always move here unless Step 2 logic pulls it into Title):**
- Vague size/audience descriptors that are now redundant with an exact spec kept in the Title (e.g. "for small and medium dogs" once exact cm is in the title)
- Synonyms of the category noun already used in the Title (e.g. Title has "Cuccia", don't also put "Letto" in Title — park the synonym in Highlights instead, it still carries long-tail search value there)
- Secondary functional details: texture/pattern (wave texture, etc.), foldability, non-slip base (if not already the headline safety feature)
- Aftercare/maintenance: washable, removable cover, detachable
- Quantity/strength refinements of a term already in the Title (e.g. Title has "suction cups", Highlights adds "4 strong suction cups" — complementary specificity, not duplication)
- Sensory/comfort adjectives (soft, cozy, comfortable) — low purchase-decision weight, cheap filler for Highlights if space remains

### Step 3 — Draft Title (≤75 chars) and Highlights (≤125 chars, comma-separated phrases)
Write both. Count characters by hand/tool — do not estimate. Leave a few characters of buffer where practical (don't max out to exactly 75/125) since accent marks and Amazon's own counting method can vary slightly by locale.

### Step 4 — Factual-accuracy check (do not skip)
If any modifier meaning "artificial/faux/synthetic" (Kunst-, sztuczne, Faux, Sztuczne, Konstgjord, Sintética, etc.) qualifies a material word (fur, rabbit, leather...), it must NEVER be dropped for character budget — dropping it misrepresents the material to the buyer. If space is genuinely too tight, cut something else (color, a secondary feature) before cutting this modifier.

### Step 5 — Keyword-duplication check
For both fields together: no single word/phrase (excluding prepositions/articles/conjunctions) should appear more than 2 times total. When the same root word legitimately needs to appear in both Title and Highlights (e.g. "Ventosas" / "4 ventosas potentes"), confirm the Highlights version adds genuine new information (a number, an intensifier, a specific part) rather than being a bare repeat — flag this explicitly as "complementary, not duplicate."

### Step 6 — Gap check
If the original title is missing information that matters a lot for this category and marketplace (most commonly: no dimensions given at all, or no core category noun like "for cats/dogs" present anywhere), say so explicitly and recommend the user supply it — don't silently invent data.

## Output format (always use this structure, in the user's language)

1. One line: original character count, overage amount/%, any symbol-compliance flag.
2. `## ① 短标题（Title，实测 N 字符）` — code block with the title.
3. `## ② 商品亮点（Item Highlights，实测 N 字符）` — code block with the highlights.
4. A two-column reasoning table: "留在标题" vs "迁移到亮点", each row with a one-line rationale tied to Step 2's logic (not generic "为了简洁").
5. A short "关键词重复核查" paragraph applying Step 5.
6. A compliance table: field | char count | limit | ✅/⚠️ status, plus a buffer-size callout if any field is within 1–3 characters of the limit.
7. If Step 6 found a gap, a "特别提醒" section calling it out plainly.
8. Always close by recommending the user verify final character counts in Seller Central's "审核商品信息更改" / listing-quality tool before submitting, since exact character-counting rules (accented characters, hyphens, etc.) may vary slightly by locale and haven't been fully detailed by Amazon in every language.

## Notes on language/marketplace handling

- Apply the same priority logic regardless of language — the category-specific judgment calls (e.g. "is mounting mechanism a first-order decision factor for this product type?") come from the product category, not the marketplace.
- If the pasted title is in a language/marketplace not explicitly named by the user, identify it and state which marketplace you're optimizing for before proceeding (don't silently assume).
- Product categories seen so far with worked examples to draw analogy from: pet beds (rectangular, washable cover), window hammocks/perches (suction-cup mounted), scratching mats/pads (adhesive or wall-mounted), hidden litter-box furniture, snuffle mats. When a new category appears, reason from first principles using Step 2's priority order rather than forcing it into one of these templates.
