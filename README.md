# Agent Build Pipeline Kit

A portable **PM → Spec → Build → Review → Librarian** development pipeline for
Claude Code, packaged to drop into any repo with a solid `context/` docs
architecture.

## Install (the "drop a zip, tell Claude to look" flow)

1. Unzip this kit at your repo root (it creates a `.pipeline-kit/` directory).
2. Tell Claude:

   > Read `.pipeline-kit/INSTALL.md` and install the pipeline into this repo.

3. Claude inspects the repo, fills `.pipeline-kit/pipeline.config.yml`, renders the
   skill templates against your stack/paths/tooling, wires it up, shows you the plan
   at an approval gate, and verifies the install.

When it's done you have `/lifepm`, `/spec`, `/build`, `/librarian`, `/craft`
(+ optional `/harden`, `/codexreview`) tuned to this repo.

## What you get

| Skill | Role |
|---|---|
| `/lifepm` | Product sparring before a spec — JTBD, steel-man, red-team |
| `/spec` | Feature spec (what/why + acceptance criteria) with an inline blind-review pass |
| `/build` | Live-codebase analysis → plan → test-first build → independent diff review → clean PR |
| `/librarian` | Post-ship doc pass (move spec, update living docs) |
| `/craft` | Author/refine these skills |

**Design principles baked in:** the spec carries *what/why* only — `/build` derives
the technical approach from the real code at build time; review runs on the **diff**,
not the spec; every "done" is backed by a check actually run.

## Pluggable reviewer

The independent review step adapts to what's available, best-first:
`codex-local` (watchable, subscription-billed) → `codex-headless` → Claude's
built-in `/code-review` → a manual-review stub. It degrades instead of breaking on
Linux / no-Codex environments. Any Codex path is hard-guarded to subscription auth
so it can never surprise-bill a metered API.

## Layout

```
.pipeline-kit/
  INSTALL.md            # the meta-installer — point Claude here
  pipeline.config.yml   # one source of truth; installer fills it from the repo
  templates/            # skill + script + CI templates with {{TOKEN}} placeholders
  reviewer-adapters/    # one file per reviewer option; installer picks one
```

## Requirements

- Claude Code in a git repository.
- A `context/`-style docs tree (the pipeline reads/writes specs, arch, features).
- Optional but recommended: `gh` CLI (for PRs); a reviewer (Codex CLI or Claude's
  `/code-review`); a one-command health check (`make test`, `npm run ci`, etc.).

## Re-running / upgrading

Edit `.pipeline-kit/pipeline.config.yml` and tell Claude to re-run the installer —
it re-renders cleanly from the config. Safe to commit `.pipeline-kit/` so the whole
team shares the same pipeline definition.
