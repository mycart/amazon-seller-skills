# Amazon Seller Skills

This repository is a monorepo for Codex skills used by the team.

## Skills

- `amazon-listing-optimization2`
- `amazon-ppc-campaign2`
- `ads-amazon2`

## Install

Install a single skill from this repository:

```bash
npx skills add mycart/amazon-seller-skills --skill amazon-listing-optimization2 -g
```

More examples:

```bash
npx skills add mycart/amazon-seller-skills --skill amazon-ppc-campaign2 -g
npx skills add mycart/amazon-seller-skills --skill ads-amazon2 -g
```

## Team Guide

Detailed installation notes, example prompts, and the current shared skill list
are in [TEAM-USAGE.md](/Users/apple/Documents/amazon-seller-skills/TEAM-USAGE.md).

## Sync Local Changes

After editing a local skill, run this from the repository root:

```bash
scripts/sync-skill.sh amazon-listing-optimization2 /path/to/local/amazon-listing-optimization2
```

For this machine, the current workspace copy is:

```bash
scripts/sync-skill.sh amazon-listing-optimization2 "/Users/apple/Documents/Listing优化建议/.agents/skills/amazon-listing-optimization2"
```

To sync all currently shared team skills in one go:

```bash
scripts/sync-all-team-skills.sh
```
