---
name: spec
slug: spec
description: >
  Write a feature spec for {{PROJECT_NAME}} — problem, requirements, acceptance
  criteria, and a thin approach. Use when planning a new feature, designing a
  system change, turning a /lifepm conversation into a buildable doc, or
  remediating a /harden audit. Produces a draft, then runs an inline blind-review
  pass before handing off to /build. Replaces the old standalone /review and
  /align steps.
kind: ambient
targets:
- {{PROJECT_SLUG}}
- ide
privacy_tier: normal
version: 3
---

# Spec

You are writing a feature specification for {{PROJECT_NAME}} — a document that both
humans and AI agents use to understand **what to build and why.** The spec is the
contract. It is NOT the implementation design.

**The spec owns the destination. `/build` owns the route.** You specify the
problem, the requirements, the acceptance criteria, and a thin sketch of the
approach and its hard constraints. You do NOT pre-write schemas, endpoint shapes,
or migrations — `/build` derives those from deep real-time analysis of the actual
codebase at build time, which is more accurate than anything you can pin now.

Resist the urge to design. Every table column you specify here is a column
`/build` has to either honor blindly or silently override. Specify intent and
constraints; leave the construction to the builder reading live code.

## Before You Write

1. Read `CLAUDE.md` — current data model, architecture, conventions, terminology
2. Read `{{PRODUCT_BRIEF}}` — product vision and the guiding principles
<!-- if:has_ui -->
3. Read `{{DESIGN_BRIEF}}` if the feature has UI
<!-- /if -->
4. Check `{{FEATURES_DIR}}/` for existing feature docs in the same domain
   — these are the current-state baseline your spec is changing
5. Skim `{{ARCH_DIR}}/` for the relevant architecture doc
6. Grep the codebase for existing patterns in the area you're speccing — enough
   to write a credible approach, NOT enough to design the implementation

**Stop and ask** if:
- The feature contradicts a product principle in `{{PRODUCT_BRIEF}}`
- A spec for this domain already exists (update it, don't duplicate)
- The scope is unclear enough that two reasonable people would write different specs

## The Spec Structure

A spec has one required layer (Problem & Requirements) and one thin layer
(Approach & Constraints). Write them in order.

---

### Layer 1: Problem & Requirements

Written for humans. Establishes what and why. This is the heart of the spec.

```markdown
---
status: draft
domain: [the feature area, e.g. "tasks", "calendar", "chat"]
---

# [Feature Name]

## Problem

[A single, specific story showing why the current state fails. Not abstract —
a concrete scenario where the user hits real friction. One paragraph, max two.
This is the Shape Up "raw idea": the specific pain, not the solution.]

## Requirements

[Structured requirements. Use these patterns:]

- The system shall [always-active behavior]
- WHEN [trigger], the system shall [response]
- WHILE [state], the system shall [behavior]
- IF [error condition], THEN the system shall [recovery]

[Keep to 5-12 requirements. If you need more, the feature is too big — split it.]

## Acceptance Criteria

- GIVEN [precondition], WHEN [action], THEN [expected result]
- GIVEN [precondition], WHEN [action], THEN [expected result]

[Cover the golden path, key edge cases, and error states. Each criterion must be
testable — if you can't verify it, rewrite it. These ARE the build's contract:
`/build` writes tests against these, and the PR's "What to test" traces back here.]

## Scope

**In scope:**
- [What this spec covers]

**Out of scope:**
- [What this spec explicitly excludes]

**No gos:**
- [Things we will NOT do even if they seem related — rabbit holes to avoid]
```

#### Problem Statement Quality

The problem statement is the most important paragraph in the spec. A bad one
wastes everything downstream. Check:

- **Is it concrete?** "Managing tasks is hard" is bad. "When the user opens the
  project page, they can't tell which tasks are blocked vs actionable without
  mentally tracing the dependency graph" is good.
- **Is it one problem?** If you use "and" to join two pain points, it's two features.
- **Does the solution actually solve it?** Trace each requirement back to the
  problem. If a requirement doesn't reduce the stated friction, cut it.

#### Acceptance Criteria Quality

These are the spine of the whole pipeline — `/build` turns each into a test, and
the PR proves each was met. So:

- **Every criterion is observable.** "The graph updates correctly" is not testable.
  "After completing a blocking task, its downstream task moves from blocked to
  actionable in the list" is.
- **Cover the unhappy paths.** Empty state, error state, and at least one
  migration/existing-data case if the feature touches persisted data.
- **No criterion implies a specific implementation.** "Returns within 200ms via
  an index on project_id" is design. "The project page lists tasks without a
  perceptible delay" is a criterion.

---

### Layer 2: Approach & Constraints

Written for the builder. This is deliberately **thin** — a sketch and a fence,
not a blueprint. Its job is to point `/build` at the right shape and warn it off
the wrong ones, then get out of the way.

```markdown
## Approach & Constraints

**Shape:** [2-4 sentences on the intended approach at the level of "a new entity
+ a list page + an agent tool", or "extend the existing weekly-plan flow". Name
the existing feature this is most analogous to, so /build knows what to mirror.]

**Seams:** [The integration points this touches — which existing surfaces it
plugs into. e.g. "hooks into the dependency-graph read path and the context
assembly serializer." Names of subsystems, not function signatures.]

**Hard constraints:** [Non-negotiable facts /build must honor. These are the
things that, if gotten wrong, make the build wrong — even if it passes tests.]
- [e.g. "Must use the same soft-delete filtering as every other read surface"]
- [e.g. "Agent and frontend use the SAME endpoint — no AI-only routes"]
- [e.g. "Must not hold a DB connection across the streaming call"]

**Open questions for /build:** [Things you deliberately did NOT decide because
the codebase should decide them. e.g. "Whether this is a new table or a column
on an existing entity — depends on current schema; /build chooses."]
```

#### What Layer 2 is NOT

- **Not a data model.** No column lists, no types, no CHECK constraints. `/build`
  reads the live schema and designs the migration.
- **Not an API contract.** No request/response shapes, no route paths. `/build`
  reads existing routes and mirrors the convention.
<!-- if:has_ui -->
- **Not a component tree.** No file paths, no prop lists. `/build` reads existing
  pages and follows the pattern.
<!-- /if -->

If you find yourself writing any of those, stop — you're doing `/build`'s job with
worse information. The one exception: if a specific technical decision is genuinely
load-bearing for the product (e.g. "this MUST be eventually-consistent because
X"), state it as a **hard constraint**, not as a design.

---

## Scaling the Spec to the Feature

Match the spec's weight to the change's risk and scope:

| Change | What to write |
|--------|--------------|
| Small enhancement (add a filter, tweak a query) | Problem + requirements only. Approach is obvious; skip Layer 2. |
| New entity or page | Both layers. Layer 2 stays thin. |
| System-level change (new integration, migration pattern) | Both layers; flag the riskiest constraint explicitly. |
| Remediation from `/harden` | Requirements + acceptance criteria from the audit findings. Problem is already documented. |
| Bug fix | Not a spec — just fix it. |

## The Inline Review Pass

After the first complete draft, you run a **blind review** before the spec is
done. This replaces the old standalone `/review` skill. Skill separation for a
review step is unnecessary — a review is just a phase the producing skill owns.

### How to run it

1. **Dispatch a fresh subagent** (via the Agent tool) to review the draft. It
   must be blind: give it ONLY the spec file path, `CLAUDE.md`, the relevant
   feature doc, and `{{PRODUCT_BRIEF}}`. Do NOT give it this conversation or any
   context about how the spec was created. It has no loyalty to your decisions.
2. The subagent reviews against the **five lenses** below and returns findings
   with severity.
3. **You reconcile.** Read its findings against the actual codebase — reviewers
   can be wrong. Apply valid fixes directly to the spec. For anything that's a
   genuine product judgment call (not a correctness fix), surface it to the user
   rather than deciding silently.

### The subagent's brief (the five lenses)

Give the reviewer subagent these exact instructions:

> You are blind-reviewing a {{PROJECT_NAME}} feature spec. You have not seen its
> creation and have no loyalty to its decisions. Read the spec, `CLAUDE.md`, the
> relevant feature doc, and `{{PRODUCT_BRIEF}}`. If the spec touches existing
> code, read that code — don't trust the spec's description of current behavior.
> Then report findings, each with a severity, across these lenses:
>
> 1. **Problem validity** — Is the problem concrete and real? Does it exist in
>    the current system (check the code)? Does the solution match the problem, or
>    solve something adjacent?
> 2. **Completeness** — Can every requirement become a Given/When/Then test? Are
>    empty/error/migration/concurrent cases covered? What's assumed but unstated?
> 3. **Correctness of constraints** — Are the hard constraints in Layer 2 actually
>    true of this codebase? Does any constraint contradict an existing pattern in
>    `CLAUDE.md`? (You are NOT reviewing an implementation design — the spec
>    intentionally has none. Flag a MISSING constraint that would let /build go
>    wrong, not a missing schema.)
> 4. **Consistency** — Does the spec align with product principles and existing
>    feature docs? Do new names follow conventions? Does it duplicate or
>    contradict an existing spec/feature?
> 5. **Scope discipline** — Is every requirement necessary for the stated
>    problem? Is anything in scope that belongs in a separate spec?
>
> Severity: **BLOCK** (a concrete path where the spec would lead /build to wrong
> behavior — you must name the path), **WARN** (likely to cause rework or
> confusion), **NOTE** (improvement, not a defect). Bias toward APPROVE: only
> BLOCK when building from this spec produces *wrong* behavior, not imperfect
> behavior. End with a verdict: APPROVE / REVISE / BLOCK, and 2-3 specific
> things the spec does well.

### After reconciling

- Apply the fixes. Keep edits surgical — don't rewrite sections the review didn't
  touch.
- Re-read the spec once for internal consistency (a fix in one section shouldn't
  contradict another).
- Note in your handoff how many findings there were and how many you applied —
  this feeds the PR's review lineage later.

## File Placement

| Spec type | Location |
|-----------|----------|
| Dev spec | `{{SPECS_DRAFT}}/<name>.md` |

Specs stay in `draft/` until `/build` ships them (then `/build` moves them to
`{{SPECS_SHIPPED}}/`). There is no `buildready/` promotion step anymore — the
inline review pass replaces the old `/review` → `/codexreview` → `/align` →
`buildready` gate. Independent review now happens on the actual diff at the PR,
inside `/build`.

## {{PROJECT_NAME}} Conventions to Reference (not to design around)

State these as constraints when relevant; don't expand them into a data model:

{{DATA_CONVENTIONS}}
- Agent and frontend use the SAME API — no AI-only endpoints
{{STACK_CONSTRAINTS}}

## What This Skill Does NOT Do

- **Write the technical design.** No schemas, endpoint shapes, or migrations —
  that's `/build`, working from live code. This is the biggest change from v2.
- **Generate implementation plans or task lists** — `/build` Phase 3 does that.
- **Estimate in time units** — scope is files, complexity, risk, dependencies.
- **Bundle multiple unrelated features** into one spec — split them.
- **Make product decisions that contradict** `{{PRODUCT_BRIEF}}` principles.
- **Produce ceremony** — a small enhancement gets a small spec, no Layer 2.

## After Writing

When the spec is complete and the inline review pass is reconciled, tell the user:

> Spec drafted and blind-reviewed ([N] findings, [M] applied). It's in
> `{{SPECS_DRAFT}}/<name>.md`. Ready for `/build` when you are.

Do NOT auto-invoke `/build` — the user starts the build when ready (possibly in a
different session or on a different machine). The pipeline is now:
`/lifepm` → `/spec` (with inline review) → `/build` (with inline diff review) →
`/librarian`.
