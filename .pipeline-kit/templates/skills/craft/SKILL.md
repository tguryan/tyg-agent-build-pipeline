---
name: craft
slug: craft
description: >
  Write or refine a Claude Code skill in .claude/skills/. Use when creating a new
  development-workflow skill, improving an existing one, fixing a skill that
  under-triggers or drifts, or adding evals or bundled scripts to a skill. Encodes
  the current Agent Skills best practices: progressive disclosure, eval-driven
  authoring, and code as a first-class ingredient.
kind: ambient
targets:
- ide
privacy_tier: normal
version: 3
---

# Craft

You are writing a Claude Code skill — a directory under `.claude/skills/` that
teaches future Claude instances how to perform a specific development workflow
reliably.

A good skill encodes **what a senior engineer would tell a new teammate** about a
workflow: what to read first, the steps, the judgment calls, the mistakes to
avoid. Ground every decision in the canonical reference:
`{{RESEARCH_DIR}}/skill-authoring-best-practices.md` (refreshed against Anthropic's
Agent Skills launch and the skill-creator eval tooling). Read it before authoring.

## Before You Write Anything

### Is this actually a skill?

A skill codifies a **recurring workflow** that needs both structured steps and
judgment. Not everything qualifies:

| What it actually is | Why not a skill | Do this instead |
|---|---|---|
| A one-off task | No recurrence | Just do the task |
| A project-wide rule | Applies every turn | Add to CLAUDE.md |
| A code convention | Derivable from the codebase | Let existing code teach |
| A pure-automation checklist | No judgment | Write a script — and if a skill needs that script, **bundle it in the skill** (see Code) |

A skill IS worth writing when the workflow has recurred (or the user commits to
future use), it mixes concrete steps with judgment, a fresh instance would need
real context to do it right, and getting it wrong has meaningful cost.

### Pre-flight

1. **Read `.claude/skills/README.md`** (the manifest) — does a skill for this
   already exist? If yes, refine it; don't duplicate.
2. **Is this premature?** One-off → suggest staying ad-hoc. Explicit commitment to
   future use counts as the second case.
3. **Scope:** one skill, one workflow. If the body would exceed ~500 lines or ~15
   steps, it's two skills, or the detail belongs in `references/`.

### Research the domain first

A skill that encodes stale or generic knowledge teaches bad habits across every
future invocation. Before writing procedure steps:

- **Search the web** for current best practices and known pitfalls for the
  specific technologies the skill covers. Your training data has a cutoff — verify.
- **Read the actual codebase** so the skill teaches what THIS project does,
  validated against what the ecosystem recommends.

Bar: if you're less than ~90% sure a checklist item reflects current best
practice, search before writing it.

## Skill Anatomy

```
my-skill/
  SKILL.md           # required: frontmatter + procedure
  references/        # optional: detail loaded on demand (one level deep)
  scripts/           # optional: scripts the skill runs or reads
  assets/            # optional: templates, fixtures, examples
```

### Frontmatter

{{PROJECT_NAME}} skills carry these keys (<!-- if:agents_mirror -->mirrored to `.agents/skills/` by
`{{MIRROR_CMD}}`; <!-- /if -->entrypoints validated by
`{{CONTRACT_VALIDATOR}}`):

```yaml
---
name: kebab-case-name      # matches the directory
slug: kebab-case-name
description: >             # the discovery surface — see below
  ...
kind: ambient             # ambient | persona
targets:                  # ide (or other configured targets)
- ide
privacy_tier: normal      # normal | protected | private
version: 1
---
```

Optional fields worth knowing (declare them when they apply):
- `allowed-tools` — an honest declaration of the tools the skill uses.
- `disable-model-invocation: true` — for destructive or user-only skills, so the
  model can't auto-fire them; the user must invoke explicitly.

The skill's entrypoint must be exactly one of `SKILL.md` or `skill.md` (the
validator rejects both-present or neither), and the manifest path must match.

### The description is the whole ballgame for discovery

It's the only thing Claude sees at startup when deciding whether to load the skill.
Structure: **[what it does] + [when to use it] + [trigger phrases]**, third person.

- **Good:** "Write a feature spec for {{PROJECT_NAME}}. Use when planning a new feature,
  designing a system change, or turning a /pm conversation into a spec."
- **Bad:** "Help with specs." (no artifact, no triggers, no context)

Rules:
- **Third person** — first/second person degrades discovery when injected into a prompt.
- **Lead with the verb**, name the **artifact**, list **"Use when…"** triggers.
- **Lean pushy.** Claude measurably *under*-triggers skills. A missed trigger is
  the common failure, not an over-eager one — so over-include trigger surface, and
  sanity-check it against a shouldn't-fire list (see Evals).
- **No truncation.** Write the description as a complete thought — a description
  cut off mid-sentence (a real past bug here) silently degrades discovery.

### Body

A procedure a fresh instance can follow with no prior conversation:

1. **Role statement** — one sentence.
2. **What to read first** — specific paths, not "check the docs".
3. **The procedure** — numbered steps, each starting with a verb.
4. **Boundaries** — what the skill does NOT do; common mistakes; scope limits.
5. **Output format** — if it produces an artifact, define the exact shape.

### Step design & the freedom spectrum

Match instruction freedom to fragility:

| Freedom | Form | When |
|---|---|---|
| **Low** | exact command / script | fragile ops, exact sequences |
| **Medium** | pattern + acceptable variation | a preferred approach exists |
| **High** | guidelines | genuinely multiple valid approaches |

Default to **medium**. Low only where variation breaks things (narrow bridge over
a cliff); high only where judgment genuinely rules (open field).

### Boundaries section (high value)

Telling the agent what NOT to do outperforms telling it what to do. Every skill
needs explicit: out-of-scope items, common mistakes, what it does NOT handle, and
the rationalizations an agent might use to skip steps (and why they're wrong).

### Output format & examples

If the skill produces an artifact, show the exact structure as a fenced template —
agents follow structured formats more reliably than prose. One concrete example
beats three paragraphs of description; if quality depends on taste, include a
short good-vs-bad comparison.

## Code Is a First-Class Ingredient

**This reverses the old stance — skills CAN and often SHOULD ship scripts.**
Bundle a script (in `scripts/`) when an operation is fragile, deterministic, or
repeated. Three wins: more reliable than code the agent regenerates each time;
token-efficient (the script's source never enters context, only its output); and
consistent across invocations.

Rules when bundling code:
- **Signal intent:** "**Run** `x.sh` to …" (execute) vs "**See** `x.py` for the
  algorithm" (read for reference).
- **No voodoo constants** — `TIMEOUT=30  # HTTP completes within 30s`, not `=47`.
- Handle errors and use clear exit codes — the script is part of the skill's contract.
- Forward slashes in all paths, always.

The `/codexreview` skill is the worked example: it bundles
`scripts/codex-review.sh` (the `codex exec` wrapper it runs) and
`references/review-templates.md` (the prompts it fills in).

## Eval-Driven Authoring

The headline modern practice, and it matches the project's TDD discipline: write the
evals before you over-write the prose, then add only the instructions needed to
pass them. Put them in `<skill>/references/evals.md`.

1. **Find the gap.** Run the workflow WITHOUT the skill on a representative task.
   Record where it fails. That's the baseline.
2. **Write evals before prose.** 2-3 task scenarios (a prompt, any inputs, and the
   *expected behaviors* — not exact output), plus a **trigger eval**: ~5-10
   should-fire prompts and ~3-5 shouldn't-fire prompts.
3. **Write the minimum instructions** that make the evals pass. Nothing more.
4. **Iterate against observed behavior**, not imagined behavior.

You don't need an external harness — run each scenario through a fresh subagent
(Agent tool) with the skill loaded, then grade the output against the expected
behaviors with a second subagent. See `spec/references/evals.md` and
`build/references/evals.md` for the established pattern.

## Quality Checklist

Before saving:

- [ ] Description: third person, verb-led, names the artifact, lists triggers,
      leans pushy (won't under-fire), not truncated
- [ ] Frontmatter has the required keys; `allowed-tools` /
      `disable-model-invocation` declared if they apply
- [ ] SKILL.md under ~500 lines; detail moved to `references/` (one level deep)
- [ ] Every step starts with a verb; single responsibility each
- [ ] Explicit boundaries / "what NOT to do" section
- [ ] Output format fully defined if it produces an artifact; examples concrete
- [ ] A bundled script where an op is fragile/deterministic/repeated (not prose)
- [ ] An `references/evals.md` with trigger evals + task scenarios
- [ ] No time-sensitive content (dates, version numbers that rot)
- [ ] Doesn't copy CLAUDE.md/AGENTS.md (reference them) or explain what Claude knows
- [ ] A fresh instance with no conversation context could follow it

## Anti-Patterns

| Pattern | Problem | Fix |
|---|---|---|
| Vague description ("helps with X") | never triggers | what + when + triggers |
| First/second-person description | discovery failure | third person |
| Under-stuffed triggers | under-firing (the common failure) | lean pushy; check shouldn't-fire set |
| Truncated description | silent discovery loss | write a complete thought |
| 30+ step monolith | fatigue, drift | split, or move detail to `references/` |
| Nested references (a → b → c) | agent only partially traverses | keep refs one level deep |
| Windows paths / voodoo constants in scripts | break or confuse | forward slashes; document constants |
| Offering 5 equal options | paralysis | one default + escape hatch |
| Copying CLAUDE.md into the skill | drift, conflicts | reference it |
| "Be thorough" / "be careful" | not actionable | name the specific checks |
| No evals | regressions invisible | add `references/evals.md` |
| "Skills can't contain code" | outdated; loses reliability | bundle the script |

## Refining an Existing Skill

1. Read the current skill fully.
2. Identify what's not working — under-triggering, drift, observed misses, user feedback.
3. Make the **minimal targeted edit**. Don't rewrite what works.
4. If it has grown past ~500 lines, split detail into `references/`.
5. Bump `version`. Re-run the skill's evals (or add them if missing).
6. **Update the wiring** (enforced by `{{CONTRACT_VALIDATOR}}`):
   the `.claude/skills/README.md` manifest, the CLAUDE.md "Development Skills"
   table<!-- if:agents_mirror -->, then regenerate the mirror with `{{MIRROR_CMD}}`<!-- /if -->.

## What This Skill Does NOT Do

- Make architecture decisions (flag and ask)
- Generate skills from imagination — skills codify observed patterns, not invented ones
- Skip the wiring update — a new/renamed skill that isn't in the manifest, the
  CLAUDE.md table<!-- if:agents_mirror -->, and the mirror<!-- /if --> will fail `{{CONTRACT_VALIDATOR}}`
