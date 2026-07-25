---
name: amazon-listing-optimization2
description: "Create and optimize Amazon listings in 12 marketplaces using product facts, keywords, competitor listings, optional CSV/XLSX keyword files, and seller-provided core selling points. Supports new-listing creation, existing-listing audits, keyword coverage and gap analysis, 8-dimension scoring, listing rewrites, competitive comparison, Chinese diagnostics, full Excel report export, and three ranked July 2026 Title + Item Highlights options. Preserve the legacy 200-character title workflow as a compatibility reference while generating a recommended 75-character Title and 125-character Item Highlights pair under Amazon's 2026 rules. Use for Amazon listing creation, optimization, SEO coverage, relaunch preparation, title/highlights generation, and report export."
---

# Amazon Listing Optimization 2 📝

Build keyword-optimized listings from scratch, or audit and optimize existing ones. No API key — works out of the box.

## Installation

```bash
npx skills add nexscope-ai/Amazon-Skills --skill amazon-listing-optimization -g
```

## Two Modes

| Mode | When to Use | Input | Output |
|------|-------------|-------|--------|
| **A — Create** | Building a new listing | Keywords and/or competitor ASINs + product info + tone | Full listing copy + keyword coverage score |
| **B — Optimize** | Improving an existing listing | Your ASIN or URL (+ optional keywords or competitor ASINs) | Optimized listing copy + audit report + gap analysis |

## Mode A — Four Ways to Start

| Input Source | How it Works |
|-------------|-------------|
| **Keywords** | User provides keyword list → skill prioritizes and generates listing |
| **Competitor ASINs** | User provides 1-3 competitor ASINs → skill fetches their listings, extracts their keywords, then generates a listing that covers all their keywords and more |
| **Both** | User provides keywords + competitor ASINs → skill merges both sources for maximum coverage |
| **Uploaded keyword files** | User provides CSV/XLSX keyword files → skill extracts relevant terms and metrics, then merges them into the keyword pool |

## Capabilities

- **Keyword-driven listing generation**: Import keywords (from amazon-keyword-research, manual list, or extracted from competitor ASINs), rank by priority, generate copy that maximizes keyword coverage
- **Competitor keyword extraction**: Fetch competitor listings and automatically extract their title/bullet keywords as your baseline
- **8-dimension audit & scoring**: Title, bullets, description, images, A+ content, pricing, reviews, SEO coverage
- **Keyword coverage tracking**: Visual map showing which keywords appear in title / bullets / description / missing
- **Tone selection**: Professional, Friendly, Urgent, Luxury — affects AI copywriting style
- **Competitive benchmarking**: Compare your listing against competitors
- **Uploaded keyword file enrichment**: If the user supplies CSV/XLSX keyword files, extract relevant keyword candidates and metrics, merge them into the keyword pool, and filter out low-relevance terms
- **Core selling point integration**: If the user provides core selling points, convert them into compliant differentiators and weave them into title, bullets, description, Item Highlights, and recommendations where relevant
- **Chinese explanatory output**: Keep all explanatory, diagnostic, audit, strategy, and recommendation text in Chinese while preserving marketplace-language listing copy
- **July 2026 ranked title options**: After listing generation or audit/rewrite, add 3 scored Title + Item Highlights combinations; keep the legacy title as a compatibility reference and mark Option 1 as the current recommended upload pair
- **Full Excel report export**: Write the complete listing output, July 2026 options, audit report, keyword analysis, before/after changes, selling point notes, and recommendations into a user-downloadable `.xlsx` file for both Mode A and Mode B
- **Multi-marketplace**: US, UK, DE, FR, IT, ES, JP, CA, AU, IN, MX, BR

## External Web Data Retrieval Priority

Apply this priority only when the task requires information from an external webpage, such as an Amazon product page, competitor listing, Seller Central help page, Amazon announcement, or public research page. It does not change any listing-generation, keyword, audit, scoring, or Excel logic.

1. **Use Chrome first** when the `Chrome` plugin and `Chrome:control-chrome` skill are available. Read and follow that skill, reuse the user's existing Chrome session where appropriate, open the target page, and extract only information visibly supported by the page.
2. Treat Chrome retrieval as successful only when the intended page and the fields needed for the task are available and attributable to the correct URL, marketplace, and product.
3. If Chrome is unavailable, cannot connect, cannot load the target page, or returns incomplete target data after a reasonable attempt, fall back to the existing method for that workflow: bundled script, purpose-built connector/API/CLI, `web_fetch`, or `web_search` as applicable.
4. Follow the Chrome skill's authentication policy. If it requires the user to sign in or approve switching away from explicitly requested Chrome, ask the user instead of bypassing authentication through another source.
5. Never infer missing webpage fields. Mark unavailable data explicitly and continue only with verified user data or verified fallback-source data.

## Usage Examples

### Mode A — Create from Keywords

```
Create a listing for a portable blender. Keywords: portable blender, smoothie maker, USB rechargeable, travel blender, personal blender. Material: BPA-free Tritan. Color: White. Capacity: 380ml. Tone: Friendly.
```

```
I have these keywords from my research: [paste keyword list]. Product: silicone kitchen utensil set, 12 pieces, heat resistant to 480°F. Generate a full listing.
```

### Mode A — Create from Competitor ASINs

```
I want to sell a dog t-shirt on Amazon US. Here are 3 competitors I want to beat: B0D72TSM62, B0ABC12345, B0XYZ67890. My product is 100% cotton, 6 colors, XS-XL, funny print. Analyze their listings and create one that's better. Friendly tone.
```

```
Create a listing for my yoga mat. Look at this competitor: B09V3KXJPB. Extract their keywords, find what they're missing, and build a listing that covers more keywords than them. Product: 6mm TPE, non-slip, carrying strap included. Tone: Professional.
```

### Mode A — Create from Keywords + Competitor ASINs

```
Use amazon-keyword-research to find keywords for "portable blender", also analyze these competitors: B0CPY1GFVZ, B0CXLF3Y19. Combine all keywords and create a listing. Product: 380ml, USB-C, BPA-free Tritan. Tone: Professional.
```

### Mode A — Create with Uploaded Keyword Files

```
Create a listing for my portable blender using the uploaded keyword CSV/XLSX files. Product: 380ml, USB-C, BPA-free Tritan, white. Use relevant high-value keywords only.
```

### Mode B — Optimize Existing

```
Audit the listing for ASIN B0D72TSM62 on Amazon US
```

```
Optimize B0D72TSM62 using these keywords: dog shirt, pet clothes, puppy clothing — show me what's missing and rewrite
```

```
Optimize my listing B0D72TSM62 by analyzing these competitors: B0ABC12345, B0XYZ67890. Find what keywords they have that I don't, and rewrite my listing to beat them.
```

```
Optimize B0D72TSM62 using the uploaded keyword XLSX files as an additional keyword source, but ignore unrelated keywords.
```

---

## Optional Uploaded Keyword Files — Applies to Mode A and Mode B

Only run this logic when the user uploads or clearly references one or more keyword files in `.csv` or `.xlsx` format. If no such files are provided, skip this section completely and continue with the normal workflow.

When keyword files are provided:

1. Extract keyword rows from every provided file. Prefer the bundled script:

```bash
<skill>/scripts/extract-keyword-files.py --output "<keywords-json>" "<file1.csv>" "<file2.xlsx>"
```

2. Recognize keyword columns using common headers such as `keyword`, `keywords`, `search term`, `search query`, `query`, `term`, `phrase`, `关键词`, `搜索词`, `关键字`, `词根`, `流量词`, `长尾词`.
3. Preserve useful metric columns when present: search volume, rank, frequency, clicks, CTR, CVR, conversion rate, orders, sales, relevancy, difficulty, competition, source file, sheet name.
4. Normalize keywords by trimming whitespace, lowercasing where appropriate for the marketplace language, removing exact duplicates, and merging metrics from repeated terms.
5. Filter for product relevance before using the terms:
   - Keep terms that clearly describe the product type, compatible use cases, material, size, audience, problem solved, or directly adjacent category.
   - Downgrade or exclude terms for unrelated products, incompatible materials/specs, competitor-only brand names, prohibited claims, medical claims, or words that would mislead shoppers.
   - If a high-volume term has weak relevance, put it in an "Excluded / Low Relevance" note instead of forcing it into the listing.
6. Merge file-derived keywords with the normal keyword sources. Do not let file keywords override better evidence from competitor listings, user-specified priority keywords, or product facts; use them to enrich and validate the keyword pool.
7. In the diagnostic output, mention the uploaded keyword file names, how many keyword candidates were extracted, how many were used, and examples of excluded low-relevance terms.

Priority guidance:
- High relevance + strong metric evidence → eligible for Title or Item Highlights.
- High relevance + medium metric evidence → bullets or description.
- Specific long-tail terms → description or backend search terms.
- Low relevance, misleading, or unsupported terms → exclude.

## Optional Core Selling Points — Applies to Mode A and Mode B

Only run this logic when the user provides product core selling points, differentiators, advantages, pain points solved, feature priorities, or purchase reasons in the prompt or attached materials. If no selling points are provided, skip this section and continue with the normal workflow.

When core selling points are provided:

1. Extract each selling point as a product fact or value proposition, such as material advantage, patent/design, compatibility, safety feature, ease of use, durability, included accessories, target scenario, or problem solved.
2. Validate each point against Amazon-safe copy rules:
   - Keep factual, product-specific, and shopper-relevant claims.
   - Avoid unsupported superlatives such as "best", "#1", "top rated", "guaranteed results".
   - Avoid medical, cure, safety-certification, environmental, or performance claims unless the user provides clear support.
   - Do not invent proof, test results, certificates, review claims, or guarantees.
3. Map selling points into the existing listing structure without changing the core workflow:
   - Title: use only the strongest 1 differentiator if it fits naturally and does not crowd the primary keyword.
   - July 2026 Title: if a compliant differentiator can be extracted, include the strongest one in all 3 candidates immediately after or naturally integrated with the core product phrase, ahead of child size and color. Omit it only when no verified differentiator can be extracted.
   - Item Highlights: use compact, complementary material/spec/use-case modifiers or scenario terms; allow only the controlled quantified refinement defined in Step C1.
   - Bullets: assign one core selling point per bullet where possible, pairing the benefit with a relevant keyword.
   - Description: expand the strongest benefits into shopper-friendly problem-solution language.
   - Backend search terms: never place unsupported claims or misleading selling points there.
   - Image/A+ recommendations: mention selling points that need visual proof, such as size reference, material layers, what's included, or use scenarios.
4. Preserve keyword logic: selling points support relevance and conversion, but they do not override primary keyword priority, keyword coverage, marketplace language, character limits, or product accuracy.
5. In the diagnostic output, include a concise Chinese section explaining which selling points were used, where they were integrated, and which were excluded or softened for compliance.

## Mode A Workflow — Create Listing from Keywords

### Step A1: Collect Keywords

Keywords can come from five sources (use one or combine multiple):

1. **From [amazon-keyword-research](https://github.com/nexscope-ai/Amazon-Skills/tree/main/amazon-keyword-research) skill** (recommended): Run keyword research first, then feed results directly. Install: `npx skills add nexscope-ai/Amazon-Skills --skill amazon-keyword-research -g`
2. **From competitor ASINs**: User provides 1-3 competitor ASINs → use Chrome first to open each marketplace product page → if Chrome does not return complete target data, run `<skill>/scripts/fetch-listing.sh` on that ASIN → extract keywords from verified titles, bullets, and descriptions → use as your keyword baseline.
3. **From user's keyword list**: User pastes their own keyword list (e.g. from Helium 10 Cerebro, Jungle Scout, or manual research)
4. **From uploaded keyword files**: User provides one or more CSV/XLSX files → run the optional uploaded keyword file workflow → merge relevant terms into the keyword pool
5. **Auto-discover**: Use Chrome first to inspect current Amazon search/category pages or relevant public webpages; if Chrome retrieval fails or is incomplete, use `web_search` to find product-category terms.

When competitor ASINs are provided, always fetch and analyze them first using the external web data retrieval priority above. Extract every meaningful keyword from verified titles and bullets, then merge with any user-provided keywords. The goal: cover everything competitors cover, plus relevant keywords they missed.

When keyword files are provided in Mode A, process them before prioritization. Use them to enrich keyword coverage, not to replace the product facts or to force unrelated keywords into the listing.

### Step A2: Prioritize Keywords

Organize keywords into tiers:

```
🔴 Primary (must appear in Title):
  - [keyword] — [search volume if known]
  - [keyword] — [search volume if known]

🟡 Secondary (must appear in Bullets):
  - [keyword]
  - [keyword]

🟢 Tertiary (should appear in Description or Backend):
  - [keyword]
  - [keyword]

⚪ Long-tail (use where natural):
  - [keyword phrase]
  - [keyword phrase]
```

Priority rules:
- Highest search volume → Title (front-loaded)
- Medium volume + high relevance → Bullets (one primary keyword per bullet)
- Lower volume / long-tail → Description
- Remaining → Backend search terms (advise seller to add in Seller Central)

### Step A3: Collect Product Characteristics

Ask or extract from user input:
- **Product name / type**
- **Brand name**
- **Key attributes**: Material, color, size, weight, capacity, quantity
- **Key features**: What makes it different (3-5 features)
- **Core selling points**: User-provided differentiators, strongest benefits, pain points solved, proof points, or launch priorities
- **Target audience**: Who buys this?
- **Use cases**: Top 3 scenarios
- **What's in the box**: Everything included

### Step A4: Select Tone

| Tone | Style | Best for |
|------|-------|----------|
| **Professional** | Authoritative, spec-focused, trust-building | Electronics, tools, B2B |
| **Friendly** | Conversational, benefit-focused, relatable | Kitchen, lifestyle, gifts |
| **Urgent** | Scarcity-driven, action words, problem-solving | Health, safety, seasonal |
| **Luxury** | Premium, sensory language, exclusivity | Beauty, fashion, premium goods |

Default: **Professional** if not specified.

### Step A5: Generate Listing Copy

Generate each component following these rules:

**Title (max 200 characters):**
- Format: `[Brand] + [Primary Keyword] + [Key Attribute 1] + [Key Attribute 2] + [Secondary Keyword] + [Differentiator]`
- Primary keyword as close to the front as possible (after brand)
- No ALL CAPS except brand name
- No promotional claims ("best", "#1", "top rated")
- Include size/color/quantity if relevant to search
- If user-provided core selling points exist, include the strongest compliant differentiator only when it improves relevance and still keeps the title natural

**Bullet Points (5 bullets, max 500 chars each):**
- Each bullet: `[BENEFIT HEADER IN CAPS] — [Benefit explanation with keyword naturally embedded]`
- Bullet 1: Primary feature + primary keyword
- Bullet 2: Key use case + secondary keyword
- Bullet 3: Quality/material + trust signal
- Bullet 4: What's included / compatibility
- Bullet 5: Guarantee / differentiator / social proof hint
- Each bullet should contain at least 1 target keyword
- If core selling points are provided, map them into bullet benefits naturally; do not force every selling point if it creates repetition or unsupported claims

**Description (max 2000 characters):**
- Opening: Problem/pain point the product solves
- Middle: Features → benefits (expand on bullets, don't repeat verbatim)
- Close: Call to action + what's in the box
- Embed remaining keywords not used in title/bullets
- Use provided core selling points to strengthen the problem → solution flow, while keeping claims factual and compliant
- Use line breaks for readability

### Step A6: Keyword Coverage Score

After generating, produce a coverage map:

```
## Keyword Coverage Report

| Keyword | Volume | In Title? | In Bullets? | In Description? | Status |
|---------|--------|-----------|-------------|-----------------|--------|
| portable blender | 45,000 | ✅ | ✅ | ✅ | 🟢 Covered |
| smoothie maker | 22,000 | ❌ | ✅ | ✅ | 🟡 Add to title |
| USB rechargeable | 18,000 | ✅ | ✅ | ❌ | 🟢 Covered |
| travel blender | 12,000 | ❌ | ❌ | ✅ | 🟡 Add to bullets |
| mini blender | 8,000 | ❌ | ❌ | ❌ | 🔴 Missing |

Coverage: 18/22 keywords (82%)
Title keywords: 6/8 slots used
Bullet keywords: 12/15 target keywords covered
Uncovered → recommend for Backend Search Terms
```

**Scoring:**
- 🟢 90%+ coverage = Excellent
- 🟡 70-89% = Good, minor gaps
- 🔴 <70% = Needs work, significant keywords missing

---

## Mode B Workflow — Optimize Existing Listing

### Step B1: Fetch Listing Data

Use Chrome first to open the product URL for the requested Amazon marketplace and extract the visible listing data. Confirm that the loaded page matches the requested ASIN and marketplace.

If Chrome is unavailable or does not return complete target data, run the bundled script:

```bash
<skill>/scripts/fetch-listing.sh "<ASIN>" [marketplace]
```

**Parameters:**
- `ASIN` (required): e.g. B09V3KXJPB
- `marketplace` (optional): `us` (default), `uk`, `de`, `fr`, `it`, `es`, `jp`, `ca`, `au`, `in`, `mx`, `br`

**Extracts:** Title, brand, price, bullet points, description, image count, A+ content presence, rating, review count, BSR, categories, date first available.

If the script also returns incomplete data, fall back to `web_fetch` on the product URL. Do not invent fields that remain unavailable.

### Step B2: Discover Target Keywords

If user provides keywords, use those. If user provides CSV/XLSX keyword files, process those files and merge relevant terms into the target keyword pool. Otherwise, auto-discover:

1. Extract apparent keywords from current title and bullets
2. Use Chrome first to inspect current Amazon search/category results for the target marketplace; if Chrome retrieval fails or is incomplete, run `web_search` for `site:amazon.com "[product type]"` to find competitors
3. Extract keywords from top 3 competitor titles and bullets
4. (Optional) Chain with `amazon-keyword-research` skill for deeper analysis
5. Add relevant terms extracted from uploaded keyword CSV/XLSX files, if provided
6. Compile a combined keyword list with estimated priority

Uploaded keyword files are supplemental in Mode B. Use them to find missing opportunities and strengthen gap analysis, but do not mark unrelated file terms as gaps that must be inserted.

If the user provides core selling points in Mode B, extract them before gap analysis and use them as product facts. They should inform the rewrite and recommendations, but they are not "keyword gaps" by themselves unless they also correspond to relevant search terms.

### Step B3: Keyword Gap Analysis

Compare current listing against target keywords:

```
## Keyword Gap Analysis: [ASIN]

### ✅ Keywords Found in Listing
| Keyword | In Title | In Bullets | In Description |
|---------|----------|------------|----------------|
| [kw] | ✅ | ✅ | ❌ |

### ❌ Missing Keywords (Competitors Have, You Don't)
| Keyword | Competitor 1 | Competitor 2 | Competitor 3 | Priority |
|---------|-------------|-------------|-------------|----------|
| [kw] | ✅ Title | ✅ Bullet | ❌ | 🔴 High |

### Coverage: X/Y keywords (Z%)
```

### Step B4: 8-Dimension Audit

Score each on the scale shown, with keyword integration factored in:

| Dimension | Max Score | Key Criteria |
|-----------|-----------|-------------|
| **Title** | /15 | Primary keyword near front? Brand? Attributes? Under 200 chars? Not truncated on mobile? |
| **Bullet Points** | /15 | All 5 used? Benefit-first? Keywords embedded naturally? Under 500 chars each? |
| **Images** | /15 | 7+ images? White bg main? Infographic? Lifestyle? Size ref? Video? |
| **A+ Content** | /10 | Present? Brand story? Comparison chart? Lifestyle imagery? |
| **Description** | /10 | Keywords not in title/bullets? Readable? Problem→solution flow? |
| **Pricing** | /10 | Competitive? Coupon/deal present? |
| **Reviews** | /15 | 4.0+ stars? 100+ reviews? Recent reviews positive? |
| **SEO Coverage** | /10 | Primary kw in title+bullets+desc? Long-tail present? No wasted repeats? **Keyword coverage %** |

### Step B5: Generate Optimized Copy

Rewrite the listing incorporating missing keywords:
- Show **before vs after** for each component
- Highlight which keywords were added and where
- Maintain the brand's existing tone unless a different tone is requested
- Integrate user-provided core selling points into the rewritten title, bullets, description, Item Highlights, and recommendations where relevant and compliant
- If the current listing already expresses a selling point well, preserve or refine it rather than rewriting it away

---

## Shared Post-Generation Steps — Applies to Mode A and Mode B

Run these steps after the standard Mode A listing generation or Mode B listing optimization is complete.

### Step C1: Add July 2026 Title + Item Highlights Options

After the standard listing output is complete, add a separate July 2026 Title + Item Highlights section. Preserve the existing listing title and its 200-character workflow unchanged for compatibility, but label it `旧版兼容参考标题，不作为2026新规首选上架标题`. Treat Option 1 below as the current recommended upload pair.

Before generating these options, read:
- `references/amazon-title-policy-2026.md` for enforceable title and Item Highlights rules.
- `references/search-ai-evidence.md` for the evidence boundaries around Amazon SEO/A9, COSMO, and Rufus/Alexa for Shopping.

Generate **3 candidates**, validate them, score them, then sort them by actual score, except for the explicit insufficient-facts branch below. Renumber the sorted candidates so the highest score is always Option 1:
- **Option 1 — Balanced recommended**: Prioritize natural language, core identity, factual attributes, and cross-field complementarity.
- **Option 2 — Keyword coverage**: Use only relevant keywords supported by user data, Amazon data, or product evidence.
- **Option 3 — Intent answerability**: Strengthen factual use cases and attributes that help answer shopper questions without inventing claims.

Build each pair by deciding what shoppers need to know first, then allocate the verified facts between fields. Do not mechanically split the legacy title or use one rigid attribute order.

Apply this sequence:

1. Build a fact pool from user materials, verified listing data, and supported keyword data. Never add an unsupported attribute.
2. Answer "what is it?" with the brand and a natural, precise core product phrase in the Title.
3. Extract differentiator candidates from verified product facts. A differentiator must be factual, product-specific, and capable of distinguishing the product from ordinary alternatives, such as mounting method, specific material, structural mechanism, connector capability, compatibility, quantified performance, or a distinctive included component.
4. Select the strongest differentiator by evidence reliability, category purchase-decision value, degree of differentiation, keyword evidence, character cost, and marketplace-language naturalness.
5. Put the strongest verified differentiator immediately after the core product phrase, or integrate it naturally into that phrase, before child size and color. Apply this requirement to all 3 candidates.
6. After the differentiator, evaluate child variation identifiers and other hard-fit information such as dimensions, capacity, model, or compatibility.
7. Move quantified expansion, secondary structure/function, care, audience, use case, and lower-priority facts to Item Highlights.
8. Confirm that the fields form a useful summary-and-detail pair rather than a mechanical split or duplicate.

Do not classify color, size, ordinary category attributes, or broad wording such as soft, comfortable, high quality, or premium as a differentiator by themselves. Competitor wording and keyword data may help prioritize a verified product fact, but they may not create a differentiator that the product evidence does not support.

Use this adaptive Title pattern as a decision guide, not a fixed word order:

`[Brand] + [core product phrase] + [strongest verified differentiator] + [child size/color] + [remaining specification]`

- Keep the Title at 75 visible characters or fewer, including spaces.
- Make the Title identify the product without relying on Item Highlights.
- Order facts naturally for the target marketplace; never produce a keyword collage.
- When a verified differentiator exists, every candidate must include it immediately after or naturally integrated with the core product phrase. A candidate that omits it or places child size/color before it must be rewritten before validation and scoring.
- If two verified differentiators are complementary and both fit naturally, place both before child size/color; only the strongest differentiator is mandatory.
- Include necessary color and size identifiers for child ASINs after the differentiator; omit specific color and size from parent ASINs.
- If no verified differentiator can be extracted from any reliable source, omit it rather than inventing one and write `未提取到可验证差异化卖点` in the Chinese `core_strategy` explanation.
- The absence of a differentiator does not permit invented or redundant Item Highlights. If all verified facts are already consumed by product identity and required child variation attributes, continue the existing evidence-gathering workflow. If no additional verified fact remains, report `资料不足，无法生成可上架的商品亮点` in Chinese and stop before candidate validation and scoring. Keep the existing `title_options_2026` interface as an empty array for this exception; do not create placeholder options, scores, or upload-ready statuses.
- Do not force every slot into the Title. Stop when the next fact would reduce clarity, crowd out product identity, or exceed the limit.
- When the Title approaches 75 characters, move secondary functions, use cases, care details, and ordinary specifications to Item Highlights before removing the strongest differentiator.
- If brand, core product phrase, strongest differentiator, and necessary child variation identifiers still cannot fit after concise natural rewriting and compact unit formatting, flag the conflict and do not mark that candidate as ready for upload.
- When candidates are otherwise equal, prefer the shorter natural Title and retain practical character headroom. Do not describe headroom as an Amazon policy requirement.
- Treat "information value per character" only as an internal selection heuristic, never an Amazon ranking formula.

Build Item Highlights from the most useful verified facts left after Title selection. Prioritize, as applicable:

`[quantified refinement], [secondary structure/function], [performance or safety specification], [care or sensory detail], [audience or use case]`

- Keep Item Highlights at 125 visible characters or fewer, including spaces.
- Use comma-separated phrases, not complete sentences.
- Never put `|` into either Seller Central field; use it only as a report delimiter when explicitly needed.
- Let the same attribute appear in either field according to decision value, keyword evidence, character cost, and available space. Material or care information is not permanently assigned to one field.
- Prefer a specific term over a generic synonym. For example, keep `Kunstkaninchenfell` and remove semantically redundant `Kunstfell`.
- Use secondary category synonyms only when user data or Amazon data supports their relevance and they add useful coverage.
- Prefer objective wording such as `für Fensterbänke`; do not add unsupported wording such as `ideal`, `beste`, `#1`, or `Bestseller`.

Allow controlled cross-field refinement when the Title names a category-critical attribute and Item Highlights add concrete, supported detail needed to explain it:

- Allowed: `Ventose` → `4 ventose potenti` because Item Highlights add the verified count and complete the installation detail.
- Allowed: `Saugnäpfe` → `4 starke Saugnäpfe bis 18 kg` when the count and load claim are verified.
- Rewrite: `waschbar` → `waschbar` because it adds no information.
- Rewrite: `Kunstfell` + `Kunstkaninchenfell` because the generic and specific terms waste semantic space; retain the specific term.
- An adjective alone is not sufficient refinement. Require a supported count, measurement, specification, structure, compatibility, use, or other concrete fact.
- Cross-field reuse does not count toward the Title's within-field repeated-word check. Continue checking the Title itself independently.
- Record every retained controlled refinement in `deduplication_notes` in Chinese and state exactly what the second field adds.

Use these positive benchmarks to learn the allocation logic without copying their product facts into unrelated listings:

- Italian window cat hammock: `CareCooo Amaca per Gatti da Finestra, Ventose, Coniglio, 52x30cm, Bianco` places the mounting and material differentiators before size and color; Item Highlights expand `Ventose` to `4 ventose potenti` and carry folding, load, softness, and care details.
- German dog bed: `CareCooo Hundebett, Kunstkaninchenfell, waschbar, M 63x53x18cm, weiß` places the specific material differentiator before size and color; Item Highlights carry dog-size suitability, shape, texture, anti-slip, care, and comfort details.
- German cat window bed: `CareCooo Fensterliege für Katzen, Saugnäpfe, M, Grau, 52x30x20cm` keeps a verified mounting differentiator before variation attributes; retain `Kunstkaninchenfell` elsewhere and remove the redundant generic term `Kunstfell`.

Before scoring, enforce the differentiator gate: if reliable evidence supports a compliant differentiator but any candidate omits it or places size/color before it, rewrite that candidate. The existing 100-point rubric applies only after this gate and the 75/125-character policy checks pass.

Validate every candidate with:

```bash
<skill>/scripts/validate-title-highlights.py --title "<title>" --item-highlights "<item-highlights>" --marketplace "<marketplace>"
```

Rewrite any candidate with hard errors before scoring. Treat warnings as review prompts and resolve material repetition or wording issues before finalizing.

Score each passing candidate with this internal review rubric:
- `fact_accuracy_and_answerability`: /25 — Product facts are accurate and directly answerable by Rufus/Alexa-style shopper questions.
- `natural_search_relevance`: /25 — Primary terms are relevant, evidence-backed, and naturally expressed; do not invent A9 weights.
- `mobile_clarity`: /20 — The Title is clear, concise, grammatical, and independently understandable.
- `field_complementarity`: /15 — Item Highlights add useful information; verified controlled refinement does not lose points, while exact or semantic waste must be rewritten.
- `intent_and_use_case`: /15 — COSMO-style intent and use-case coverage is useful but remains factual.

The total is a **skill internal review score**, never an Amazon official algorithm score. Use A9 only as industry shorthand for traditional lexical SEO, COSMO only for public semantic-intent principles, and Rufus/Alexa only for factual answerability. Amazon has not published field weights for these systems. Break ties by less unproductive repetition, then more natural language, then shorter Title length.

Each final option must include these backward-compatible and additive fields:
- Existing: `option`, `title`, `title_characters`, `item_highlights`, `item_highlights_characters`, `core_strategy`.
- Additive: `rank`, `status`, `score`, `score_breakdown`, `deduplication_notes`. Use `deduplication_notes` for both removed redundancy and retained summary-to-detail refinement.

For every candidate, write `core_strategy` in Chinese to name the selected strongest differentiator, state its verified selection basis, and confirm that it appears immediately after or is naturally integrated with the core product phrase before child size/color. If no compliant differentiator is available, use the required `未提取到可验证差异化卖点` statement instead. In `deduplication_notes`, explain in Chinese any quantified expansion of that differentiator in Item Highlights and what concrete information the second field adds; also record removed exact or semantic redundancy.

For complete, passing candidates, set Option 1 `status` to `recommended_for_current_upload`; set Options 2-3 to `alternate`. Keep all listing copy in the target marketplace language and all strategy explanations in Chinese.

### Step C2: Export Complete Listing Optimization Report to Excel

At the end of either Mode A or Mode B, create a visually friendly Excel file containing **all final output and supporting diagnostics**, not only the July 2026 Title + Item Highlights options section. Prefer the bundled script:

```bash
<skill>/scripts/write-listing-report-xlsx.py --input "<listing-report-json>" --output "<output-xlsx>"
```

The Excel file must include every major section shown in the chat response:
- Final ready-to-use listing: legacy compatibility-reference title, bullet points, description, backend search terms.
- July 2026 Title + Item Highlights options, placed in the same `Listing` sheet after the standard listing fields, using the same two-column layout (`模块` / `内容`), with Option 1 clearly marked as the current recommended upload pair.
- Mode A diagnostic data or Mode B audit report, depending on task mode.
- Keyword coverage, priority breakdown, and keyword gap analysis when available.
- Before/after changes for Mode B.
- Issues fixed, seller-action recommendations, and what was already working.
- Core selling point integration notes when selling points were provided.
- Uploaded keyword file summary when CSV/XLSX keyword files were provided.
- Competitive comparison when requested.

Create the JSON input during the task with this structure. Include empty arrays/objects for sections that do not apply:

```json
{
  "asin": "B09V3KXJPB or NEW-LISTING",
  "mode": "A or B",
  "marketplace": "US",
  "product": "Product name",
  "brand": "Brand",
  "generated_at": "2026-07-01",
  "listing": {
    "title": "Final title",
    "bullets": ["Bullet 1", "Bullet 2", "Bullet 3", "Bullet 4", "Bullet 5"],
    "description": "Final description",
    "backend_search_terms": "comma-separated backend terms"
  },
  "title_options_2026": [
    {
      "option": 1,
      "rank": 1,
      "status": "recommended_for_current_upload",
      "title": "Brand Core Keyword Attribute",
      "title_characters": 28,
      "item_highlights": "Searchable secondary keywords and specs",
      "item_highlights_characters": 40,
      "core_strategy": "Why this combination was chosen",
      "score": 94,
      "score_breakdown": {
        "fact_accuracy_and_answerability": 24,
        "natural_search_relevance": 23,
        "mobile_clarity": 19,
        "field_complementarity": 14,
        "intent_and_use_case": 14
      },
      "deduplication_notes": ["删除泛化材质词；保留标题概括、亮点量化的受控复现"]
    }
  ],
  "diagnostic": {
    "tone": "Professional",
    "keywords_imported": 25,
    "title_characters": 128,
    "description_characters": 1100
  },
  "audit": {
    "price": "$29.99",
    "rating": "4.5",
    "review_count": "125",
    "score_before": "68/100",
    "score_after": "88/100",
    "dimensions": [
      {"dimension": "标题", "before": "/15", "after": "/15", "key_change": "中文说明"}
    ]
  },
  "keyword_coverage": [
    {"keyword": "portable blender", "volume": "45000", "in_title": "yes", "in_bullets": "yes", "in_description": "yes", "status": "covered"}
  ],
  "keyword_priority": {
    "primary": ["keyword"],
    "secondary": ["keyword"],
    "tertiary": ["keyword"],
    "backend": ["keyword"]
  },
  "keyword_gaps": [
    {"keyword": "keyword", "competitor_1": "Title", "competitor_2": "Bullet", "competitor_3": "", "priority": "High"}
  ],
  "before_after": [
    {"section": "标题", "before": "original", "after": "optimized", "added_keywords": ["kw1", "kw2"]}
  ],
  "issues_fixed": ["中文说明"],
  "recommendations": ["中文建议"],
  "working_well": ["中文说明"],
  "selling_point_notes": ["中文说明"],
  "uploaded_keyword_file_summary": ["中文摘要"],
  "competitive_comparison": [
    {"dimension": "标题评分", "your_listing": "/15", "competitor_1": "/15", "competitor_2": "/15", "competitor_3": "/15"}
  ]
}
```

Workbook requirements:
- Use separate sheets for the major sections where possible: `总览`, `Listing`, `审核报告`, `关键词覆盖`, `关键词优先级`, `关键词缺口`, `优化前后`, `建议与卖点`, and `竞品对比`.
- Do not create a separate `2026标题方案` sheet. Merge the 2026 Title + Item Highlights options into the `Listing` sheet and keep the original `Listing` sheet layout style.
- Keep sheet names Chinese and under Excel's 31-character limit.
- The Excel content must mirror the response content. Do not export only the short title + highlights options.
- Label `listing.title` as `旧版兼容参考标题` and include the note `旧版兼容参考标题，不作为2026新规首选上架标题`; do not change how that legacy title is generated.
- If any section is unavailable, keep the sheet with a clear Chinese note such as `本次任务未提供该部分数据`.

文件名需要清晰，例如：`listing-optimization-report-<ASIN-or-product>-2026.xlsx`。创建完成后，在回复中提供文件路径。

---

## 输出格式

主要交付物始终是卖家可以直接复制到 Seller Central 的 **可用 Listing**。诊断数据、评分和关键词分析放在后面作为支撑依据。

### Mode A 输出 — 新建 Listing

```
# ✅ 可直接使用的Listing

## 标题（旧版兼容参考）
[旧版兼容标题文本，仅供参考]

> 旧版兼容参考标题，不作为2026新规首选上架标题。现行上架优先使用下方方案1的商品标题和商品亮点。

## 五点描述
1. [利益点标题] — [包含关键词的文案]
2. [利益点标题] — [包含关键词的文案]
3. [利益点标题] — [包含关键词的文案]
4. [利益点标题] — [包含关键词的文案]
5. [利益点标题] — [包含关键词的文案]

## 产品描述
[产品描述文本，可直接复制到 Seller Central]

## 后台搜索词
[用逗号分隔的关键词，可粘贴到 Seller Central → Keywords → Search Terms]

## 2026年7月标题 + 商品亮点方案

### 方案 1
【排名】1
【状态】现行推荐上架方案
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【技能内部选优分】[score]/100（不是Amazon官方算法分）
【分项评分】[score breakdown]
【跨字段互补与去重说明】[deduplication notes]
【核心策略简析】[中文策略说明]

### 方案 2
【排名】2
【状态】备选方案
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【技能内部选优分】[score]/100（不是Amazon官方算法分）
【分项评分】[score breakdown]
【跨字段互补与去重说明】[deduplication notes]
【核心策略简析】[中文策略说明]

### 方案 3
【排名】3
【状态】备选方案
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【技能内部选优分】[score]/100（不是Amazon官方算法分）
【分项评分】[score breakdown]
【跨字段互补与去重说明】[deduplication notes]
【核心策略简析】[中文策略说明]

---

# 📊 生成逻辑与诊断

**目标站点：** Amazon [XX] | **语气：** [tone] | **导入关键词数：** [count]
**标题字符数：** [X]/200 | **描述字符数：** [X]/2000

## 关键词覆盖率：[X]%

| 关键词 | 搜索量 | 标题中 | 五点中 | 描述中 | 状态 |
|---------|--------|----------|------------|----------------|--------|
| [kw] | [vol] | ✅/❌ | ✅/❌ | ✅/❌ | 🟢🟡🔴 |

## 关键词优先级拆解
🔴 一级词（标题）：[list]
🟡 二级词（五点）：[list]
🟢 三级词（描述）：[list]
⚪ 后台词：[list]

## 核心卖点融入说明
[仅在用户提供核心卖点时输出：说明哪些卖点被使用、分别融入到哪里、哪些卖点因合规或相关度原因被排除或弱化]

## 上传关键词文件摘要
[仅在用户提供 CSV/XLSX 关键词文件时输出：文件名、提取关键词数量、实际使用数量、被排除的低相关关键词示例]

## Excel文件
[已创建完整报告文件路径：listing-optimization-report-[product-or-ASIN]-2026.xlsx]
```

### Mode B 输出 — 审核 + 优化 Listing

```
# ✅ 优化后Listing

## 标题（旧版兼容参考）
[优化后的旧版兼容标题文本，仅供参考]

> 旧版兼容参考标题，不作为2026新规首选上架标题。现行上架优先使用下方方案1的商品标题和商品亮点。

## 五点描述
1. [利益点标题] — [优化后文案]
2. [利益点标题] — [优化后文案]
3. [利益点标题] — [优化后文案]
4. [利益点标题] — [优化后文案]
5. [利益点标题] — [优化后文案]

## 产品描述
[优化后产品描述，可直接复制到 Seller Central]

## 后台搜索词
[用逗号分隔的关键词，可粘贴到 Seller Central → Keywords → Search Terms]

## 2026年7月标题 + 商品亮点方案

### 方案 1
【排名】1
【状态】现行推荐上架方案
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【技能内部选优分】[score]/100（不是Amazon官方算法分）
【分项评分】[score breakdown]
【跨字段互补与去重说明】[deduplication notes]
【核心策略简析】[中文策略说明]

### 方案 2
【排名】2
【状态】备选方案
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【技能内部选优分】[score]/100（不是Amazon官方算法分）
【分项评分】[score breakdown]
【跨字段互补与去重说明】[deduplication notes]
【核心策略简析】[中文策略说明]

### 方案 3
【排名】3
【状态】备选方案
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【技能内部选优分】[score]/100（不是Amazon官方算法分）
【分项评分】[score breakdown]
【跨字段互补与去重说明】[deduplication notes]
【核心策略简析】[中文策略说明]

---

# 📊 审核报告：[ASIN]

**产品：** [title] | **品牌：** [brand]
**价格：** [price] | **评分：** [stars]（[count] 条评论）

## 评分：[X/100] → [Y/100]（优化后）

| 维度 | 优化前 | 优化后 | 关键变化 |
|-----------|--------|-------|-----------|
| 标题 | /15 | /15 | [中文说明] |
| 五点描述 | /15 | /15 | [中文说明] |
| 图片 | /15 | — | [仅建议，不改写] |
| A+内容 | /10 | — | [仅建议，不改写] |
| 描述 | /10 | /10 | [中文说明] |
| 价格 | /10 | — | [中文观察] |
| 评论 | /15 | — | [中文观察] |
| SEO覆盖 | /10 | /10 | [中文说明] |

> 必须保留完整详细的“审核报告”展示，不能改名为“审核摘要”，也不能只输出概要。审核报告至少包含评分表、关键词覆盖、优化前后对比、已修复问题、建议、原Listing优点，以及可用时的核心卖点和上传关键词文件摘要。

## 关键词覆盖率：[X]% → [Y]%

| 关键词 | 优化前 | 优化后 | 添加位置 |
|---------|--------|-------|-------------|
| [kw] | ❌ | ✅ | 标题 + 五点2 |
| [kw] | 仅标题中有 | 标题 + 五点中均有 | 五点4 |

## 修改对比（优化前 → 优化后）

**标题：**
> ❌ [原文]
> ✅ [优化后]

**五点：**
> ❌ 1. [原文]
> ✅ 1. [优化后，新增：+[kw1]、+[kw2]]

## 🔴 已修复问题
1. [原问题 → 修复方式]

## 🟡 需要卖家配合的建议
1. [图片、A+内容、价格等需要卖家操作的建议]

## 🟢 原Listing中表现较好的部分
1. [保留的优点]

## 核心卖点融入说明
[仅在用户提供核心卖点时输出：说明哪些卖点被使用、分别融入到哪里、哪些卖点因合规或相关度原因被排除或弱化]

## 上传关键词文件摘要
[仅在用户提供 CSV/XLSX 关键词文件时输出：文件名、提取关键词数量、实际使用数量、被排除的低相关关键词示例]

## Excel文件
[已创建完整报告文件路径：listing-optimization-report-[ASIN]-2026.xlsx]
```

### 竞品对比（如用户要求）

```
| 维度 | 你的Listing | 竞品1 | 竞品2 | 竞品3 |
|-----------|-------------|-------------|-------------|-------------|
| 标题评分 | /15 | /15 | /15 | /15 |
| 五点评分 | /15 | /15 | /15 | /15 |
| 图片 | [数量] | [数量] | [数量] | [数量] |
| A+内容 | 是/否 | 是/否 | 是/否 | 是/否 |
| 关键词覆盖率 | X% | X% | X% | X% |
| 价格 | — | — | — | — |
| 评分 | — | — | — | — |
| **总分** | **/100** | **/100** | **/100** | **/100** |
```

### 关键原则

1. The seller's workflow is: **copy the listing → paste into Seller Central → done.** The diagnostic section explains WHY those specific words were chosen, but the listing itself must stand alone as a complete, ready-to-use deliverable. Never output only a report without the actual listing copy.

2. **Listing copy language must match the target marketplace.** Amazon US/UK/AU/CA/IN → English. Amazon DE → German. Amazon FR → French. Amazon JP → Japanese. Amazon ES/MX → Spanish. Amazon IT → Italian. Amazon BR → Portuguese. This applies to the actual listing copy fields: title, bullet points, description, backend search terms, July 2026 Title, and Item Highlights.

3. **Explanatory text must be Chinese.** All section headings, diagnostic notes, audit explanations, strategy briefs, issue summaries, recommendations, keyword analysis explanations, core selling point integration notes, and Excel/file delivery notes in the response must be written in Chinese. This requirement does not translate the actual marketplace listing copy unless the target marketplace language is Chinese or the user explicitly asks for Chinese copy.

4. **Preserve the original workflow.** Keep the legacy 200-character Title/Bullets/Description workflow for compatibility and label its Title as reference-only. The July 2026 Title + Item Highlights section remains in the same output position, but Option 1 is the current recommended upload pair. Do not alter the legacy title-generation formula or any non-title workflow.

5. **Excel export is required for Mode A and Mode B full report delivery.** Whenever a listing is generated or optimized, also generate the `.xlsx` file unless the runtime cannot write files. The workbook must include the complete final listing output and all available diagnostic/audit sections, not only the July 2026 title options. If file creation fails, explain the failure and still show all required sections in the response.

6. **Uploaded keyword files are optional enrichment.** Use CSV/XLSX keyword files only when the user provides them. They expand the keyword evidence base for both Mode A and Mode B, but they must never force irrelevant, inaccurate, prohibited, or misleading keywords into the listing.

7. **Core selling points are optional conversion evidence.** Use user-provided selling points only when present. Integrate them into listing optimization where they improve relevance, clarity, and conversion, but never let them override keyword prioritization, character limits, marketplace language, product facts, or Amazon-safe claim rules.

8. **Mode B must show the detailed audit report.** The response heading must remain `审核报告`, not `审核摘要`. Do not collapse the audit into a short summary; preserve the detailed audit structure from the output template.

## Integration with amazon-keyword-research

This skill works best when chained with [amazon-keyword-research](https://github.com/nexscope-ai/Amazon-Skills/tree/main/amazon-keyword-research):

```
Step 1: "Research keywords for portable blender on Amazon US"
   → amazon-keyword-research returns keyword list with volumes

Step 2: "Now create a listing using those keywords. Product: 380ml BPA-free blender, USB-C rechargeable. Tone: Friendly."
   → amazon-listing-optimization Mode A uses the keywords to generate optimized copy
```

## Limitations

This skill uses publicly available data from Amazon product pages. It cannot access backend search terms, exact search volumes, or PPC/conversion data. For deeper analytics, check out **[Nexscope](https://www.nexscope.ai/?co-from=skill)** — Your AI Assistant for smarter E-commerce decisions.

Amazon does not publish ranking-factor weights for A9, COSMO, or Rufus/Alexa for Shopping. Never present the internal Title + Item Highlights review rubric as Amazon's official score or promise a ranking outcome.

---

**Built by [Nexscope](https://www.nexscope.ai/?co-from=skill)** — research, validate, and act on e-commerce opportunities with AI.
