#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  ads-amazon2 \
  "/Users/apple/.agents/skills/ads-amazon2" \
  "Sync ads-amazon2"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  amazon-asin-availability-monitor2 \
  "/Users/apple/.agents/skills/amazon-asin-availability-monitor2" \
  "Sync amazon-asin-availability-monitor2"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  amazon-listing-optimization2 \
  "/Users/apple/.agents/skills/amazon-listing-optimization2" \
  "Sync amazon-listing-optimization2"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  amazon-ppc-campaign2 \
  "/Users/apple/.agents/skills/amazon-ppc-campaign2" \
  "Sync amazon-ppc-campaign2"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  amazon-product-research2 \
  "/Users/apple/.agents/skills/amazon-product-research2" \
  "Sync amazon-product-research2"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  monitor-asin-sale-chrome \
  "/Users/apple/.codex/skills/monitor-asin-sale-chrome" \
  "Sync monitor-asin-sale-chrome"
