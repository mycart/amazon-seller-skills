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
  "/Users/apple/.codex/skills/amazon-listing-optimization2" \
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
  kjxj-amazon-monthly-report-analyzer \
  "/Users/apple/.agents/skills/kjxj-amazon-monthly-report-analyzer" \
  "Sync kjxj-amazon-monthly-report-analyzer"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  kjxj-amazon-listing-pipeline \
  "/Users/apple/.codex/skills/kjxj-amazon-listing-pipeline" \
  "Sync kjxj-amazon-listing-pipeline"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  kjxj-amazon-title-optimizer \
  "/Users/apple/.codex/skills/kjxj-amazon-title-optimizer" \
  "Sync kjxj-amazon-title-optimizer"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  kjxj-export-ss-data \
  "/Users/apple/.codex/skills/kjxj-export-ss-data" \
  "Sync kjxj-export-ss-data"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  kjxj-optimize-sync-listing \
  "/Users/apple/.agents/skills/kjxj-optimize-sync-listing" \
  "Sync kjxj-optimize-sync-listing"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  kjxj-sync-cloud-drive \
  "/Users/apple/.agents/skills/kjxj-sync-cloud-drive" \
  "Sync kjxj-sync-cloud-drive"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  kjxj-sync-product-listing \
  "/Users/apple/.codex/skills/kjxj-sync-product-listing" \
  "Sync kjxj-sync-product-listing"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  monitor-amazon-listing-chrome \
  "/Users/apple/.codex/skills/monitor-amazon-listing-chrome" \
  "Sync monitor-amazon-listing-chrome"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  monitor-asin-sale-chrome \
  "/Users/apple/.codex/skills/monitor-asin-sale-chrome" \
  "Sync monitor-asin-sale-chrome"
