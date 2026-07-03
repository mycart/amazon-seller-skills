# Amazon Seller Skills Team Guide

This document covers the skills currently shared from this repository and how
the team can install and use them with Codex.

## Repository

- GitHub repository: `mycart/amazon-seller-skills`

## Available Skills

- `amazon-listing-optimization2`
- `amazon-ppc-campaign2`
- `ads-amazon2`

## Install Methods

Install a single skill directly from GitHub:

```bash
npx skills add mycart/amazon-seller-skills --skill amazon-listing-optimization2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-ppc-campaign2 -g
npx skills add mycart/amazon-seller-skills --skill ads-amazon2 -g
```

If a teammate only wants one skill, they only need to run the matching command.

## Skill Use Cases

### `amazon-listing-optimization2`

Best for:

- creating a new Amazon listing from keywords
- auditing an existing listing
- generating July 2026 title and item highlights options
- exporting listing optimization results to Excel

Example prompts:

```text
Use amazon-listing-optimization2 to create an Amazon US listing for my portable blender. Brand: ACME. Keywords: portable blender, smoothie maker, USB rechargeable blender. Core selling points: USB-C charging, 380ml, BPA-free Tritan.
```

```text
Use amazon-listing-optimization2 to optimize ASIN B0XXXXXXX. Please output the full optimized listing, detailed audit report, July 2026 title options, and Excel report.
```

### `amazon-ppc-campaign2`

Best for:

- building Amazon PPC campaigns from scratch
- auditing existing PPC structure and ACoS
- analyzing search term reports
- generating bid adjustments and negative keyword actions

Example prompts:

```text
Use amazon-ppc-campaign2 to build a launch PPC structure for my Amazon US product. Price: $39.99. Cost: $8. Shipping: $3. Amazon fees: $7.50. Keywords: portable blender, travel blender, smoothie maker.
```

```text
Use amazon-ppc-campaign2 to optimize my current PPC campaigns. Overall ACoS is 58%, target is 30%, and here is my search term report data.
```

### `ads-amazon2`

Best for:

- deep Amazon Ads account audits
- Sponsored Products, Sponsored Brands, Sponsored Display, and basic DSP reviews
- portfolio structure, negative keyword discipline, TACOS and brand analytics analysis

Notes:

- this skill is best used as an Amazon Ads audit/analysis specialist
- depending on Codex environment, it may be triggered automatically from
  Amazon Ads or Amazon PPC prompts rather than being manually invoked every time

Example prompts:

```text
Use ads-amazon2 to audit my Amazon advertising account. I have Sponsored Products, Sponsored Brands, and Sponsored Display running. Review campaign structure, search-term harvesting, ACOS discipline, and brand analytics usage.
```

```text
Use ads-amazon2 to review my last 60 days of Amazon Ads reports and generate an Amazon Ads Health Score with a prioritized action plan.
```

## Ongoing Sync Workflow

This repository already includes sync scripts. After a skill is edited on the
local machine, use one of these:

Sync one skill:

```bash
cd /Users/apple/Documents/amazon-seller-skills
scripts/sync-skill.sh amazon-ppc-campaign2 "/Users/apple/.agents/skills/amazon-ppc-campaign2" "Sync amazon-ppc-campaign2"
```

Sync all currently shared team skills:

```bash
cd /Users/apple/Documents/amazon-seller-skills
scripts/sync-all-team-skills.sh
```

The current local source paths used by the repository are:

- `amazon-listing-optimization2` -> `/Users/apple/Documents/Listing优化建议/.agents/skills/amazon-listing-optimization2`
- `amazon-ppc-campaign2` -> `/Users/apple/.agents/skills/amazon-ppc-campaign2`
- `ads-amazon2` -> `/Users/apple/.codex/skills/ads-amazon2`
