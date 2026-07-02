---
name: amazon-listing-optimization2
description: "Amazon listing builder and optimizer for sellers. Two modes: (A) Create — build keyword-optimized listings from scratch using keyword lists + product characteristics + AI copywriting, (B) Optimize — audit existing listings, find keyword gaps, score across 8 dimensions, and rewrite with missing keywords. Also adds July 2026 compact title + item highlights option sets and full Excel report export for both Create and Optimize modes. Can optionally ingest user-uploaded CSV/XLSX keyword files as an extra keyword data source for both modes, and integrate user-provided core selling points into listing optimization without changing the core workflow. Explanatory, diagnostic, and strategy text in responses must be Chinese. Integrates with amazon-keyword-research for keyword input. Works on 12 Amazon marketplaces. No API key required. Use when: (1) creating a new Amazon listing from keywords, (2) auditing an existing listing for SEO and conversion, (3) checking keyword coverage in title/bullets/description, (4) generating listing copy with target keywords and tone, (5) comparing listings against competitors, (6) preparing a listing for launch or relaunch, (7) generating 2026-compliant title and item highlights options, (8) using uploaded keyword CSV/XLSX files to enrich listing keyword coverage, (9) incorporating product core selling points into Amazon listing copy, (10) exporting all listing output, audit report, keyword analysis, and recommendations to Excel."
metadata: {"nexscope":{"emoji":"📝","category":"amazon"}}
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
- **July 2026 compact title options**: After listing generation or audit/rewrite, add 3 sets of mobile-friendly Title + Item Highlights combinations without replacing the original listing output
- **Full Excel report export**: Write the complete listing output, July 2026 options, audit report, keyword analysis, before/after changes, selling point notes, and recommendations into a user-downloadable `.xlsx` file for both Mode A and Mode B
- **Multi-marketplace**: US, UK, DE, FR, IT, ES, JP, CA, AU, IN, MX, BR

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
   - July 2026 Title: use 1-2 most important differentiators only when the 75-character limit still passes.
   - Item Highlights: use compact secondary differentiators, material/spec/use-case modifiers, or scenario terms.
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
2. **From competitor ASINs**: User provides 1-3 competitor ASINs → run `<skill>/scripts/fetch-listing.sh` on each → extract keywords from their titles, bullets, and descriptions → use as your keyword baseline. This is the fastest way to start — you inherit what's already working for competitors, then add more.
3. **From user's keyword list**: User pastes their own keyword list (e.g. from Helium 10 Cerebro, Jungle Scout, or manual research)
4. **From uploaded keyword files**: User provides one or more CSV/XLSX files → run the optional uploaded keyword file workflow → merge relevant terms into the keyword pool
5. **Auto-discover**: Use `web_search` to find top keywords for the product category

When competitor ASINs are provided, always fetch and analyze them first. Extract every meaningful keyword from their titles and bullets, then merge with any user-provided keywords. The goal: cover everything competitors cover, plus keywords they missed.

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

Run the bundled script:

```bash
<skill>/scripts/fetch-listing.sh "<ASIN>" [marketplace]
```

**Parameters:**
- `ASIN` (required): e.g. B09V3KXJPB
- `marketplace` (optional): `us` (default), `uk`, `de`, `fr`, `it`, `es`, `jp`, `ca`, `au`, `in`, `mx`, `br`

**Extracts:** Title, brand, price, bullet points, description, image count, A+ content presence, rating, review count, BSR, categories, date first available.

If script returns incomplete data, fall back to `web_fetch` on the product URL.

### Step B2: Discover Target Keywords

If user provides keywords, use those. If user provides CSV/XLSX keyword files, process those files and merge relevant terms into the target keyword pool. Otherwise, auto-discover:

1. Extract apparent keywords from current title and bullets
2. Run `web_search` for `site:amazon.com "[product type]"` to find competitors
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

After the standard listing output is complete, add a separate July 2026 Title + Item Highlights options section. This is an additional output only; do not remove or replace the existing title, bullet points, description, backend search terms, keyword coverage report, or audit report.

Generate **3 different combinations**. Each combination must include:
- **Title**: 75 characters or fewer, including spaces. Formula: `[Brand] + [absolute core keyword/category] + [1-2 most important differentiating attributes or model terms]`.
- **Item Highlights**: 125 characters or fewer, including spaces. Use this field for secondary keywords and modifiers such as material, specification, use case, pack count, compatibility, or audience.
- **Core Strategy Brief**: Explain why this keyword and attribute combination was chosen.

Rules:
- Count visible characters exactly, including spaces. Do not count Markdown labels, brackets, or the parenthetical character count.
- If any Title exceeds 75 characters or any Item Highlights exceeds 125 characters, rewrite it until it passes.
- Use natural, concise language. Avoid keyword stuffing and repeated terms.
- Make sure the Title can communicate the core product on mobile without relying on the Item Highlights.
- Make the Item Highlights searchable and complementary; it should extend the Title instead of repeating it.
- If user-provided core selling points exist, use them as differentiator candidates, but only include the highest-impact compliant points that fit the 75/125-character limits.
- Output language still follows the target marketplace language rule.

### Step C2: Export Complete Listing Optimization Report to Excel

At the end of either Mode A or Mode B, create a visually friendly Excel file containing **all final output and supporting diagnostics**, not only the July 2026 Title + Item Highlights options section. Prefer the bundled script:

```bash
<skill>/scripts/write-listing-report-xlsx.py --input "<listing-report-json>" --output "<output-xlsx>"
```

The Excel file must include every major section shown in the chat response:
- Final ready-to-use listing: title, bullet points, description, backend search terms.
- July 2026 Title + Item Highlights options, placed in the same `Listing` sheet after the standard listing fields, using the same two-column layout (`模块` / `内容`).
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
      "title": "Brand Core Keyword Attribute",
      "title_characters": 28,
      "item_highlights": "Searchable secondary keywords and specs",
      "item_highlights_characters": 40,
      "core_strategy": "Why this combination was chosen"
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
- If any section is unavailable, keep the sheet with a clear Chinese note such as `本次任务未提供该部分数据`.

文件名需要清晰，例如：`listing-optimization-report-<ASIN-or-product>-2026.xlsx`。创建完成后，在回复中提供文件路径。

---

## 输出格式

主要交付物始终是卖家可以直接复制到 Seller Central 的 **可用 Listing**。诊断数据、评分和关键词分析放在后面作为支撑依据。

### Mode A 输出 — 新建 Listing

```
# ✅ 可直接使用的Listing

## 标题
[标题文本，可直接复制到 Seller Central]

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
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【核心策略简析】[中文策略说明]

### 方案 2
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【核心策略简析】[中文策略说明]

### 方案 3
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
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

## 标题
[优化后标题，可直接复制到 Seller Central]

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
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【核心策略简析】[中文策略说明]

### 方案 2
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
【核心策略简析】[中文策略说明]

### 方案 3
【商品标题】[title]（[精准字符数] 字符）
【商品亮点】[item highlights]（[精准字符数] 字符）
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

4. **Preserve the original workflow.** The July 2026 Title + Item Highlights section is a supplemental output. It must appear after the ready-to-use listing and before or within the diagnostic/audit support section, but it must not replace the standard Title/Bullets/Description deliverable.

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

---

**Built by [Nexscope](https://www.nexscope.ai/?co-from=skill)** — research, validate, and act on e-commerce opportunities with AI.
