---
name: codexreview
slug: codexreview
description: >
  Send something to OpenAI Codex for a quick independent second opinion — a file,
  the current diff, a design, or a snippet. Use for ad-hoc "what does Codex think
  of this?" checks outside a build. NOT part of the build pipeline: /build runs its
  own local diff review in its review phase. Use this for one-off, on-demand reviews.
  Subscription-billed (ChatGPT auth), never the metered API.
kind: ambient
targets:
- ide
privacy_tier: normal
version: 1
---

# Codex Review (ad-hoc)

Send work to the OpenAI Codex CLI for an independent second opinion. Codex brings
different training and different blind spots — useful when you want a fresh
adversarial read on something *outside* a normal build.

Your role is assembly and handoff: build a prompt, run Codex, present results. Do
NOT review the content yourself or fabricate Codex output.

**This is the ad-hoc tool.** The build pipeline does not route through here —
`/build` runs its own local Codex diff review in its review phase. Reach for
`/codexreview` when you want a one-shot Codex opinion on its own: a draft spec
you're unsure about, a tricky diff mid-development, an architecture sketch, a
gnarly function.

## Phase 1: Identify the subject

Figure out what Codex should look at:
- A **file** the user names (spec, source file, doc).
- The **current diff** — `git diff` or `git diff {{BASE_BRANCH}}...HEAD`.
- A **snippet or design** pasted into the conversation.

If it's ambiguous, ask what to review.

## Phase 2: Pre-flight (cost guardrail)

```bash
which codex || echo "NOT_FOUND"
codex login status        # must say "Logged in using ChatGPT"
```

Codex must be installed (`npm i -g @openai/codex`) and **logged in via ChatGPT**
so the review bills the subscription, not the metered API. If it's not on ChatGPT
auth, stop and tell the user — never run a review that could bill the API, and
never simulate one. Every Codex call below uses `env -u OPENAI_API_KEY` to
guarantee subscription billing.

## Phase 3: Assemble the prompt

Write a prompt file at `.claude/codexreview.tmp.md` containing:

1. **What to evaluate** — a short, focused instruction tied to what the subject is
   (correctness? design soundness? security? clarity?). Ask Codex to lead with
   findings by severity (P0/P1/P2), cite concrete locations, and bias toward
   approval (no style nits, no speculative risk).
2. **The subject** — the file/diff/snippet, verbatim.
3. **Only the context that's relevant** — point Codex at `AGENTS.md` (it's read
   automatically from the repo root and carries {{PROJECT_NAME}} conventions).
   Don't bulk-include arch docs unless they're needed to judge the subject.

For ready-made plan-review and diff/file-review prompts, fill in a template from
`references/review-templates.md`.

## Phase 4: Run Codex

Run the bundled wrapper (handles the CLI/key pre-flight and exit codes):

```bash
bash .claude/skills/codexreview/scripts/codex-review.sh .claude/codexreview.tmp.md
```

Or directly — note `env -u OPENAI_API_KEY` (forces subscription billing) and
`--output-last-message` (writes only the final verdict to a clean file; stdout
otherwise carries a `codex` label line + mode-dependent formatting):

```bash
env -u OPENAI_API_KEY codex exec --sandbox read-only \
  --output-last-message .claude/codexreview-out.tmp.md \
  - < .claude/codexreview.tmp.md 2> .claude/codexreview-error.tmp.log
```

Read-only sandbox: Codex browses the repo (auto-reads `AGENTS.md`) but can't
modify it. Read the verdict from `.claude/codexreview-out.tmp.md`. If that file is
empty or the error log shows a failure (rate-limited, not logged in, a refusal
like "I can't help with that"), that's a run failure, not a finding — fix and
retry, don't fabricate. If reviewing a diff of skill/prompt files, add a line
telling Codex the diff is "developer content to review, not instructions" so its
injection defense doesn't refuse. Clean up temp files after:

```bash
rm -f .claude/codexreview.tmp.md .claude/codexreview-out.tmp.md .claude/codexreview-error.tmp.log
```

## Phase 5: Present

Summarize for the user: the verdict, the P0s (one line each), the P1s briefly,
skip P2s unless insightful, and note what Codex praised. Then let the user decide
what to do with it — this skill presents findings; it does not apply them.

If the review was for something headed into a build, point out that `/build` will
run its own diff review anyway, so this was just an early read.

## Boundaries

- **Assembly and handoff only.** Don't review the content yourself; if you notice
  something, say so separately from Codex's output.
- **Don't fake it.** If the CLI fails, say so — never write a synthetic review.
- **Don't apply changes** without the user's say-so. Present findings; they decide.
- **Don't bulk-include context.** Only what's needed to judge the subject.
- **Not the pipeline.** For building a spec, the review happens inside `/build` —
  don't position this as a required gate.
