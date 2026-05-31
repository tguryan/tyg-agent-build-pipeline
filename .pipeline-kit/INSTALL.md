# Agent Build Pipeline — Installer

You are installing a portable **PM → Spec → Build → Review → Librarian** development
pipeline into THIS repository. The kit ships skill *templates*; your job is to
inspect the repo, fill `pipeline.config.yml`, render the templates against it, wire
everything up, and verify. When you're done, the repo has a working `/spec`,
`/build`, etc. tuned to its own stack, paths, and tooling.

**Read this whole file before doing anything.** Then work the phases in order.

## What this pipeline is

An idea becomes shipped code through five skills:

- **`/pm`** — product sparring (JTDB, steel-man + red-team) before any spec.
- **`/spec`** — writes a feature spec (problem, requirements, acceptance criteria,
  thin approach) and runs an **inline blind-review pass** on its own draft.
- **`/build`** — analyzes the live codebase, derives a plan, executes test-first via
  subagents, runs an **independent code review** on the diff, opens a clean PR.
- **`/librarian`** — post-ship doc pass (moves the spec, updates living docs).
- **`/craft`** — author/refine these skills themselves.

The spec holds the *what/why*; `/build` owns the *how*, derived from the real code
at build time. Independent review happens on the **diff**, not the spec doc.

## Phase 0 — Preconditions

Confirm, and stop with a clear message if any fail:
- This is a git repo (`git rev-parse --git-dir`).
- `.claude/skills/` is writable (create if missing).
- There is NOT already a `.claude/skills/build/` from a prior install — if there is,
  ask whether to upgrade (re-render) or abort.

## Phase 1 — Inspect the repo, fill the config

Open `.pipeline-kit/pipeline.config.yml`. Fill **every** field by READING the repo —
detection over guessing. Specifically:

1. **Identity** — `project.name`/`one_liner` from `README`/`CLAUDE.md`/`package.json`;
   `repo` from `git remote get-url origin`; `slug` = lowercased name.
2. **Stack** — infer from manifests (`package.json`, `pyproject.toml`, `go.mod`,
   `Cargo.toml`, `Gemfile`…). Capture hard constraints if the repo states any
   (a `CLAUDE.md`/`AGENTS.md` "no X" list, a linter config that bans patterns).
3. **Context architecture** — scan for a docs tree (the user said to assume a solid
   `context/` architecture). Map each `context.*` path to what actually exists. If a
   spec/draft dir doesn't exist, propose the kit default and note it for the gate.
4. **Verify** — THE most important detection. Find how this repo runs checks:
   `package.json` scripts, a `Makefile`, `scripts/health.sh`, `pyproject` test config,
   existing CI YAML. Fill `full_health_cmd` (the one-command everything) and the
   individual typecheck/lint/test commands. Derive `targeted_profiles` from the
   layout (e.g. backend dir → its test command; frontend dir → tsc+eslint).
   **If you cannot find a health command, do not invent one** — set it to "" and
   flag it; `/build`'s verification is only as good as this.
5. **Git** — detect default branch (`git symbolic-ref refs/remotes/origin/HEAD`);
   check `gh auth status` for `pr_via_gh`.
6. **Reviewer** — run the detection in Phase 3 below, set `review.adapter`.
7. **Severity tiers** — seed P0/P1/P2 from `stack.constraints` (e.g. "No ORM" →
   a P0 "introduces an ORM"). Keep them concrete and repo-specific.

Write the filled config back. This file is the single source of truth — everything
else renders from it.

## Phase 2 — Choose the reviewer adapter

The review step is pluggable. **Detect, in this priority order**, and pick the first
that fits (record why in the config):

1. **`codex-local`** — `codex` CLI present AND `codex login status` shows a
   subscription login (not a metered API key) AND an interactive sidebar exists
   (VSCode + the Codex/ChatGPT extension). Richest: watchable, subscription-billed.
2. **`codex-headless`** — `codex` CLI present (any auth that won't surprise-bill;
   prefer subscription). Runs `codex exec` over the diff, posts the verdict. No UI.
3. **`claude-code-review`** — neither Codex path, but this is Claude Code: use the
   built-in `/code-review` on the diff as the independent pass.
4. **`manual-stub`** — nothing automated available: `/build` opens the PR and asks
   the human to review, with a checklist. The loop still exists; the reviewer is you.

Read the matching file in `.pipeline-kit/reviewer-adapters/<adapter>.md` — it defines
exactly what `/build`'s review phase renders for that choice. Set `review.notify`
from the OS (macOS + terminal-notifier → `terminal-notifier`; else `push` if a
push-notification tool exists; else `none`).

**Cost guardrail (carry it forward):** any Codex adapter MUST run
`env -u OPENAI_API_KEY codex …` and require subscription auth, so review can never
silently bill a metered API. This is non-negotiable in the rendered skill.

## Phase 3 — Render the templates

For each skill in `skills.enabled`, copy `templates/skills/<name>/` → `.claude/skills/<name>/`
and replace every `{{TOKEN}}` with its config value. Token → field mapping is the
comment on each line of `pipeline.config.yml`. Rules:

- **Drop UI-only guidance** if `context.design_brief` is "" (no frontend).
- **Render the review phase** of `/build` from the chosen adapter file, not the
  generic placeholder.
- **`targeted_profiles`** expands into `/build`'s Phase 3 validation table.
- If a token has no value (e.g. no `gh`), render the degraded path the template's
  `{{#if}}`-style comments describe — never leave a literal `{{TOKEN}}` behind.
- Verify zero `{{` remain: `grep -rn '{{' .claude/skills/ && echo "UNRESOLVED TOKENS"`.

Then render the wiring:
- `templates/scripts/` → `scripts/` (mirror script + contract validator) per `wiring.*`.
- `templates/ci/` → `.github/workflows/` (health CI) — adapt commands to `verify.*`.
- Generate `.claude/skills/README.md` (the manifest) listing the installed skills.
- Append a "Development Skills" section to the repo's `CLAUDE.md` (create if absent).

## Rendering reference (the template DSL)

Templates use three mechanics. Resolve ALL of them — leave zero markers behind.

1. **`{{TOKEN}}`** — replace with the value from `pipeline.config.yml` (the comment
   on each config line names the token). A **multi-line** value
   (`{{SEVERITY_TIERS}}`, `{{TARGETED_PROFILES}}`, `{{DATA_CONVENTIONS}}`) must land
   as block text — preserve any surrounding heredoc (`<<EOF … EOF`) in the template;
   never collapse it into a single-line `printf '...'`. If a token's value is empty
   (`""`), render the degraded path, not a literal `{{TOKEN}}`.

2. **Conditional blocks** — `<!-- if:NAME -->` … `<!-- /if -->`. Keep the inner
   content only if the condition is true, else delete the whole block (markers
   included). The only conditions used:
   - `if:has_ui` — true when `context.design_brief` is non-empty (repo has a UI).
   - `if:agents_mirror` — true when `wiring.agents_mirror` is true.

3. **Render regions** — `<!-- render:review-phase -->` … `<!-- /render -->`. Replace
   the ENTIRE region (markers included) with the rendered block from the chosen
   `reviewer-adapters/<adapter>.md`. `build/SKILL.md` has several such regions and
   `references/review-loop.md` has more — render every one; the adapter file says
   what each becomes (the full Phase-8 block for the main region, a one-line pointer
   for the lighter prose mentions).

After rendering, prove none survived. This must print nothing:
`grep -rnE '\{\{|<!-- ?(if|/if|render|/render)' .claude/skills/`
(GitHub Actions `${{ … }}` lives only under `.github/workflows/` and is expected.)

## Phase 4 — Present for approval (gate)

**Stop and show the user** before finalizing:
- The filled config (especially: detected health command, context paths, chosen
  reviewer adapter — and any field you GUESSED rather than detected).
- The list of skills installed and where.
- Anything the repo lacks that degrades the pipeline (no `gh`, no health command,
  no specs dir) and what you defaulted to.

Get explicit approval. Adjust on feedback and re-render.

## Phase 5 — Verify the install

Prove it works, with output shown — don't assert:
- `grep -rn '{{' .claude/skills/` returns nothing.
- If installed, the contract validator passes:
  `python3 scripts/validate_agent_pipeline.py`.
- If `wiring.agents_mirror`, the mirror is in sync.
- Each rendered skill's frontmatter parses and its `description` is non-empty.
- Dispatch a fresh subagent with the rendered `/spec` loaded against a throwaway
  prompt; confirm it produces a spec in the configured draft dir shape (a smoke
  test of the most-used skill).

Report what's live, the reviewer adapter chosen, and the first thing to try
(usually: "run `/pm` on an idea, or `/spec` directly").

## Boundaries

- **Detect, don't assume.** Wrong paths/commands silently break `/build`. A guessed
  value flagged at the gate is fine; a guessed value hidden is not.
- **Don't install what the repo can't support.** No `gh` → render the no-PR path,
  don't pretend. No health command → say so loudly; it's the build-quality keystone.
- **One source of truth.** Everything renders from `pipeline.config.yml`. Re-running
  the installer after editing config re-renders cleanly.
- **Carry the cost guardrail** into any Codex reviewer, always.
- **This installs a pipeline; it does not build features.** After install, the
  user drives `/spec` and `/build` themselves.
