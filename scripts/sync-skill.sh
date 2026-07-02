#!/usr/bin/env bash
set -euo pipefail

SKILL_NAME="${1:?Usage: scripts/sync-skill.sh <skill-name> <local-skill-dir> [commit-message]}"
SOURCE_DIR="${2:?Usage: scripts/sync-skill.sh <skill-name> <local-skill-dir> [commit-message]}"
COMMIT_MESSAGE="${3:-Sync ${SKILL_NAME}}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="${REPO_ROOT}/${SKILL_NAME}"

if [ ! -f "${SOURCE_DIR}/SKILL.md" ]; then
  echo "ERROR: ${SOURCE_DIR} does not look like a Codex skill directory; SKILL.md was not found." >&2
  exit 1
fi

mkdir -p "${TARGET_DIR}"
rsync -a --delete \
  --exclude ".git" \
  --exclude "__pycache__" \
  --exclude ".DS_Store" \
  "${SOURCE_DIR}/" "${TARGET_DIR}/"

cd "${REPO_ROOT}"
git add "${SKILL_NAME}"
if git diff --cached --quiet; then
  echo "No changes to commit for ${SKILL_NAME}."
  exit 0
fi

git commit -m "${COMMIT_MESSAGE}"
git push origin main
