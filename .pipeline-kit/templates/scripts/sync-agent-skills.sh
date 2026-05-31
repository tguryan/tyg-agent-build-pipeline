#!/usr/bin/env bash
set -euo pipefail

# Mirror the canonical Claude Code skills tree to .agents/skills/ so other
# agent tools (Codex, Cursor, etc.) can read the same skills. The .agents/
# tree is generated — never edit it by hand. Re-run this after changing any
# skill under .claude/skills/.
#
# Repo-agnostic: derives the project root from this script's own location,
# so it works regardless of where the kit is installed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

mkdir -p "$PROJECT_DIR/.agents"
rsync -a --delete "$PROJECT_DIR/.claude/skills/" "$PROJECT_DIR/.agents/skills/"

printf "Synced .agents/skills from .claude/skills\n"
