# Amazon Seller Skills

This repository is a monorepo for Codex skills used by the team.

## Skills

- `ads-amazon2`
- `amazon-asin-availability-monitor2`
- `amazon-listing-optimization2`
- `amazon-ppc-campaign2`
- `amazon-product-research2`
- `kjxj-amazon-monthly-report-analyzer`
- `kjxj-amazon-listing-pipeline`
- `kjxj-amazon-title-optimizer`
- `kjxj-export-ss-data`
- `kjxj-optimize-sync-listing`
- `kjxj-sync-cloud-drive`
- `kjxj-sync-product-listing`
- `monitor-amazon-listing-chrome`
- `monitor-asin-sale-chrome`

## Install

Install a single skill from this repository:

```bash
npx skills add mycart/amazon-seller-skills --skill ads-amazon2 -g
```

More examples:

```bash
npx skills add mycart/amazon-seller-skills --skill amazon-asin-availability-monitor2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-listing-optimization2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-ppc-campaign2 -g
npx skills add mycart/amazon-seller-skills --skill amazon-product-research2 -g
npx skills add mycart/amazon-seller-skills --skill kjxj-amazon-monthly-report-analyzer -g
npx skills add mycart/amazon-seller-skills --skill kjxj-amazon-listing-pipeline -g
npx skills add mycart/amazon-seller-skills --skill kjxj-amazon-title-optimizer -g
npx skills add mycart/amazon-seller-skills --skill kjxj-export-ss-data -g
npx skills add mycart/amazon-seller-skills --skill kjxj-optimize-sync-listing -g
npx skills add mycart/amazon-seller-skills --skill kjxj-sync-cloud-drive -g
npx skills add mycart/amazon-seller-skills --skill kjxj-sync-product-listing -g
npx skills add mycart/amazon-seller-skills --skill monitor-amazon-listing-chrome -g
npx skills add mycart/amazon-seller-skills --skill monitor-asin-sale-chrome -g
```

## Team Guide

Detailed installation notes, example prompts, and the current shared skill list
are in [TEAM-USAGE.md](/Users/apple/Documents/amazon-seller-skills/TEAM-USAGE.md).

## Sync Local Changes

After editing a local skill, run this from the repository root:

```bash
scripts/sync-skill.sh <skill-name> /path/to/local/skill
```

To sync all currently shared team skills in one go:

```bash
scripts/sync-all-team-skills.sh
```
