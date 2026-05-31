#!/usr/bin/env bash
# Run an ad-hoc Codex review in a read-only sandbox over an assembled prompt,
# billed against the ChatGPT subscription — NOT the metered OpenAI API.
#
# Usage: codex-review.sh <prompt-file> [out-file]
#   <prompt-file>  Markdown prompt (e.g. a review-templates.md template, filled in).
#   [out-file]     Where to write Codex's stdout. Defaults to a temp file whose
#                  path is echoed on success so the caller can read it.
#
# Exit codes: 0 = review ran (read out-file for findings); 1 = usage error;
#             2 = codex CLI missing; 3 = not logged in via ChatGPT; 4 = codex failed.
# Run from the repo root. This is the ad-hoc /codexreview wrapper. The build
# pipeline runs its own local review in /build's review phase.
#
# COST GUARDRAIL: this never uses OPENAI_API_KEY. It requires ChatGPT-subscription
# auth and strips the API key from the environment (`env -u OPENAI_API_KEY`) so
# Codex cannot silently fall back to metered per-token billing.

set -uo pipefail

PROMPT_FILE="${1:-}"
OUT_FILE="${2:-.claude/codex-review-out.tmp.md}"
ERR_FILE=".claude/codex-review-error.tmp.log"

if [ -z "$PROMPT_FILE" ] || [ ! -f "$PROMPT_FILE" ]; then
  echo "usage: codex-review.sh <prompt-file> [out-file]" >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "codex CLI not found. Install with: npm i -g @openai/codex" >&2
  exit 2
fi

# Require ChatGPT-subscription auth so we never bill the metered API.
if ! codex login status 2>/dev/null | grep -qi "ChatGPT"; then
  echo "Codex is not logged in via ChatGPT. Run 'codex login' (Sign in with ChatGPT)." >&2
  echo "Refusing to run — a metered API key could otherwise be billed." >&2
  exit 3
fi

# env -u OPENAI_API_KEY: hard guarantee Codex uses the subscription, not the API.
# read-only: Codex can browse the repo (and pick up AGENTS.md) but not modify it.
# --output-last-message: codex exec writes its transcript to stderr; the final
#   message (the actual review) only lands cleanly in this file, not on stdout.
if env -u OPENAI_API_KEY codex exec --sandbox read-only \
     --output-last-message "$OUT_FILE" - < "$PROMPT_FILE" 2> "$ERR_FILE" \
   && [ -s "$OUT_FILE" ]; then
  echo "$OUT_FILE"
  exit 0
fi

echo "codex review failed (empty output or error); see $ERR_FILE" >&2
exit 4
