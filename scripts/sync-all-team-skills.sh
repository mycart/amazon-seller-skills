#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  amazon-listing-optimization2 \
  "/Users/apple/Documents/Listing优化建议/.agents/skills/amazon-listing-optimization2" \
  "Sync amazon-listing-optimization2"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  amazon-ppc-campaign2 \
  "/Users/apple/.agents/skills/amazon-ppc-campaign2" \
  "Sync amazon-ppc-campaign2"

"${REPO_ROOT}/scripts/sync-skill.sh" \
  ads-amazon2 \
  "/Users/apple/.codex/skills/ads-amazon2" \
  "Sync ads-amazon2"
