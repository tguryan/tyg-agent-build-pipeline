# Codex Review Templates (ad-hoc /codexreview)

Prompt templates for running OpenAI Codex as a one-off reviewer outside a build.
Use these when you want a fast Codex opinion on a plan, a diff, or a file.

The build pipeline does NOT use these — `/build` runs its own local diff review in
its review phase (`skills/build/references/review-loop.md`). These are only for the
ad-hoc `/codexreview` skill.

## Pre-flight (cost guardrail)

```bash
which codex || echo "NOT_FOUND"
codex login status        # must say "Logged in using ChatGPT"
```

Codex must be installed (`npm i -g @openai/codex`) and **logged in via ChatGPT**
so reviews bill the subscription, not the metered API. If it's not on ChatGPT
auth, stop and tell the user — never run a review that could bill the API, and
never simulate one. Every invocation below uses `env -u OPENAI_API_KEY` to
guarantee subscription billing.

## Invocation

Fill in a template below into a prompt file, then run the wrapper:

```bash
bash .claude/skills/codexreview/scripts/codex-review.sh <prompt-file> <out-file>
```

Or directly — note `env -u OPENAI_API_KEY` (forces subscription billing) and
`--output-last-message` (clean verdict file):

```bash
env -u OPENAI_API_KEY codex exec --sandbox read-only \
  --output-last-message .claude/codexreview-out.tmp.md \
  - < .claude/codexreview.tmp.md 2> .claude/codexreview-error.tmp.log
```

Read-only sandbox: Codex browses the repo (and auto-reads `AGENTS.md`) but can't
modify it. Read the verdict from the output file; on failure (empty output, or an
error/refusal in the error log) report it and retry — never fabricate. Clean up
temp files after.

## Severity (shared)

- **P0 — must fix:** a concrete path that breaks — wrong behavior, data loss,
  unmet requirement, security/privacy violation.
- **P1 — should fix:** likely rework or subtle bug.
- **P2 — consider:** quality improvement, not a defect.

Every finding: what's wrong, the concrete failure path (or the convention it
violates), and a fix. Tell Codex to bias toward approval and not flag style,
speculation, or pre-existing unrelated issues.

---

## Template: Plan review

~~~markdown
# Implementation Plan Review

You are reviewing an implementation plan for {{PROJECT_NAME}} before it is
executed. Find problems before code is written — wrong assumptions about the
codebase, missing steps, ordering bugs, unmet requirements. Review only; do not
rewrite the plan. AGENTS.md (repo root) has the conventions — read it first.

Tie every finding to a requirement the plan fails, a codebase fact that
contradicts a plan assumption, or a missing step that stalls execution. Flag
correctness, coverage, and ordering only — not style or extra abstraction.

## Output
### Summary — one paragraph: is this plan sound to execute?
### Findings — grouped P0/P1/P2; omit empty levels. Each: issue, the
requirement/fact it violates, failure path, **Fix:**.
### Verdict — Approve / Revise / Block.

---

## Plan Under Review
{PLAN — verbatim}

## Current Code State
{relevant snippets / arch docs the plan will touch}
~~~

---

## Template: Diff / file review

~~~markdown
# Code Review

You are reviewing changed code for {{PROJECT_NAME}}. Review the diff (or file)
below against the conventions in AGENTS.md (repo root) — read it first and apply
its P0/P1/P2 lists. Review only the changed work and its direct consequences.

Each finding cites a concrete file and line, the failure mode, and the convention
or requirement it violates. Bias toward approval: no style, no speculation, no
pre-existing issues outside this change.

## Output
### Summary — one paragraph: is this correct and safe?
### Findings — grouped P0/P1/P2; omit empty levels. Each: file:line, failure
mode, violated rule, **Fix:**.
### Verdict — Approve / Revise / Block.

---

## Subject
{DIFF (`git diff {{BASE_BRANCH}}...HEAD`) or FILE — verbatim}
~~~
