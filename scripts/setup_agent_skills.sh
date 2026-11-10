#!/usr/bin/env bash
# Restore world-top project skills from skills-lock.json (Nov 2026 leaderboard packs).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f skills-lock.json ]]; then
  echo "missing skills-lock.json in $ROOT" >&2
  exit 1
fi

echo "Restoring project skills from skills-lock.json ..."
npx skills experimental_install --no-frozen-lockfile

echo "Linking for Cursor + Claude Code ..."
npx skills experimental_sync -a cursor -a "claude-code" -y || true

echo "Done. Project skills:"
npx skills list -p 2>/dev/null | head -40 || ls .agents/skills | wc -l
