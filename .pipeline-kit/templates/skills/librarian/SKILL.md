---
name: librarian
description: Audit the context folder for staleness, misplaced files, and missing updates. Use after shipping code, after /build
  completes, or when context docs may be out of sync with the codebase.
kind: ambient
targets:
- ide
privacy_tier: normal
version: 1
---

# Librarian

You are auditing the {{PROJECT_NAME}} context folder to ensure documentation reflects the
current state of the codebase. You are a librarian — you check that everything is
filed correctly, nothing is stale, and no updates were missed.

## When This Runs

- **As the `/build` documentation phase** — `/build` delegates its documentation
  pass to this skill, as the final content of the PR before the merge call. It's a
  single pass: it's docs, so no review rounds.
- After a commit that changes data model, API surface, or frontend structure
- On request, when the user suspects docs are out of sync
- Periodically, as a hygiene check

## The Context System

```
{{CONTEXT_ROOT}}/
├── product/
│   ├── productbrief.md          # Vision, principles (evergreen)        → {{PRODUCT_BRIEF}}
│   ├── designbrief.md           # Design system (evergreen)             → {{DESIGN_BRIEF}}
│   ├── backlog.md               # Ideas queue (evergreen)
│   └── features/                # Living product truth (agent-maintained) → {{FEATURES_DIR}}
├── dev/
│   ├── setup.md                 # Dev environment
│   ├── arch/                    # Living system truth                   → {{ARCH_DIR}}
│   │   ├── backend.md
│   │   ├── frontend.md
│   │   └── currentstate.md
│   └── specs/
│       ├── draft/               # Specs being designed (and blind-reviewed in /spec) → {{SPECS_DRAFT}}
│       ├── reviews/             # Review artifacts (now diff reviews, from /build)    → {{SPECS_REVIEWS}}
│       └── shipped/             # Specs that have shipped (moved by /build)           → {{SPECS_SHIPPED}}
└── research/                    # Cross-cutting research                → {{RESEARCH_DIR}}
```

## Audit Procedure

### 1. Identify what changed

Read the recent git diff or the user's description of what shipped. Build a list of:
- New or modified database tables/columns
- New or modified API endpoints
- New or modified frontend pages/components
- New or modified agent tools
- New or modified integrations
- Architecture pattern changes

### 2. Check CLAUDE.md

For each change identified in step 1, verify CLAUDE.md reflects it:

- **Data Model section** — are new tables/columns documented? Are descriptions accurate?
- **Key API Endpoints section** — are new endpoints listed with request/response shapes?
- **Current Gaps section** — has anything moved from "gap" to "done" (or vice versa)?
- **Agent tools section** — are new tool domains or tools mentioned?
- **Terminology section** — any new terms that need defining?
- **Documentation Structure section** — does the context folder tree match reality?

### 3. Check living arch docs

- **backend.md** — if backend patterns changed (new route convention, new tool domain,
  new integration pattern, DB convention change), is it reflected?
<!-- if:has_ui -->
- **frontend.md** — if frontend patterns changed (new widget, new component pattern,
  new routing, new state management approach), is it reflected?
<!-- /if -->
- **currentstate.md** — update status markers for anything that moved from
  ○/— to ◐/✓ or vice versa. Check entity CRUD matrix, integration status,
<!-- if:has_ui -->
  frontend page status.
<!-- /if -->

### 4. Check feature docs

For each feature area touched by the changes:
- Does a feature doc exist in `{{FEATURES_DIR}}`?
- If yes: does it accurately describe the current state of that feature?
  Check for stale descriptions that don't match the code.
- If no: should one be created? (Only if the change is a substantive new capability,
  not a minor enhancement.)
- Does the lineage table include the spec that drove this change?

### 5. Check spec lifecycle

Specs flow `{{SPECS_DRAFT}}` → `{{SPECS_SHIPPED}}` (moved by `/build` when it ships).
The blind review happens inline in `/spec`, and the diff review happens in `/build`.

- Are there specs in `{{SPECS_DRAFT}}` that have actually shipped? Move them to `{{SPECS_SHIPPED}}`.
- Do review artifacts in `{{SPECS_REVIEWS}}` reference specs that no longer exist?
  (Historical — staleness is acceptable.)
- Are there specs in `{{SPECS_SHIPPED}}` that reference stale paths or patterns?
  (Historical records — minor staleness is acceptable.)
- Do any draft specs reference features or patterns that no longer exist?

### 6. Check structural health

- Are all files in the correct directory per the hierarchy?
- Do all docs have proper frontmatter (title, type, created/updated datetimes)?
  `updated` must use ISO 8601 datetime with timezone: `2026-05-02T14:50Z`.
  Date-only values (`2026-05-02`) are stale format — upgrade to datetime on touch.
- Are there orphaned files outside the hierarchy?
- Are there empty placeholder files that should be populated or removed?
- Do any docs reference old paths that predate the current `{{CONTEXT_ROOT}}/` layout
  (e.g. relocated arch, requirements, or plans directories)?

## Output Format

```markdown
## Librarian Audit

**Scope:** [what was checked — "post-ship audit for <feature>" or "full sweep"]

### Findings

#### [STALE] doc-name.md — section
What's wrong. What it says vs what the code shows.
**Fix:** [specific edit needed]

#### [MISSING] doc-name.md
What should exist but doesn't.
**Fix:** [create/update with specific content]

#### [MISPLACED] filename
File is in the wrong location.
**Fix:** [move from X to Y]

#### [ORPHAN] filename
File exists outside the hierarchy or references dead paths.
**Fix:** [move or delete]

### Summary

- X stale docs updated
- X missing docs created
- X files moved
- X issues remaining (if any need user input)
```

## Severity

- **STALE** — content doesn't match current code. Most common finding.
- **MISSING** — a doc should exist but doesn't (new feature without feature doc).
- **MISPLACED** — file is in the wrong directory.
- **ORPHAN** — file references dead paths or sits outside the hierarchy.

## After Auditing

Fix everything you can directly. Don't just report — update the docs. The only
findings that should remain in the summary as "issues remaining" are ones that
require user judgment (e.g., "should X be a new feature doc or an update to Y?").

## What This Skill Does NOT Do

- Write specs (that's `/spec`)
- Review specs for correctness (that's the inline blind review in `/spec`)
- Build features (that's `/build`)
- Make product decisions about what to build
- Rewrite docs for style — only fix factual accuracy and placement
- Delete shipped specs (they're historical records)
