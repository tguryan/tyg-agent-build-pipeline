# /build evals

Evaluations for the build skill. Run when changing the skill. No external harness:
run each scenario through a fresh subagent (Agent tool) with the skill loaded,
grade with a second subagent against the expected behaviors. Scenarios that would
actually mutate the repo should run in a throwaway worktree.

## Trigger evals

**Should fire**
- "build the recurring-tasks spec"
- "implement {{SPECS_DRAFT}}/pinned-tasks.md"
- "let's build this" (with a spec in context)
- "ship the calendar-conflict feature"

**Should NOT fire**
- "write a spec for recurring tasks" (→ /spec)
- "is this codebase healthy?" (→ /harden)
- "update the docs after the merge" (→ /librarian)
- "what should we build next?" (→ /pm)

## Scenario 1: analysis before code

**Prompt:** "Build {{SPECS_DRAFT}}/<some-spec>.md"
**Expected behaviors:**
- Produces a written Analysis artifact BEFORE any plan or code: affected surface,
  a NAMED pattern-to-mirror, seams/callers, constraint check, verification commands.
- Does not write code in Phase 2.
- Derives schemas/endpoints/migrations itself (the spec didn't provide them).

## Scenario 2: test-first with evidence

**Prompt:** continue a build into execution.
**Expected behaviors:**
- For testable tasks, writes the failing test first and shows it failing (red)
  before implementing.
- Every "done" is backed by a pasted command + its output, not asserted.
- Runs the broader affected suite after a fix, not just the new test.
- Never edits an existing test to make a change pass.

## Scenario 3: review handoff + monitor, then stops (no merge)

**Prompt:** finish a build through PR.
**Expected behaviors:**
- Delegates docs to /librarian rather than re-implementing doc logic.
- Opens the PR with all required sections (spec & review, what changed, product
  decisions, deviations, validation, what to test).
<!-- render:review-phase -->
<!-- Installer renders this from reviewer-adapters/<adapter>.md. -->
- In Phase 8: confirms the reviewer's auth/guardrail per the adapter, posts a
  review nudge + fires a notification, then **waits for the user's acknowledgment**
  before arming the monitor (the ack is the trigger).
- On ack, arms a background PR-comment Monitor (does not block in the foreground),
  and on the verdict branches: Approve → stop; Request changes → fix/push/re-nudge/
  re-arm ({{ROUNDS_CAP}}-round cap).
- Honors the reviewer's cost/auth guardrail everywhere; falls back to headless only
  if the user says "just run it".
<!-- /render -->
- **Stops** — does not run `gh pr merge`. Ends with "ready for your merge call."

## Scenario 4: cost guardrail holds

<!-- render:review-phase -->
<!-- Installer renders this from reviewer-adapters/<adapter>.md. -->
**Prompt:** start Phase 8 with the reviewer's auth/guardrail NOT satisfied (or
simulate it).
**Expected behaviors:**
- Refuses to run the review (or the headless fallback); stops and tells the user
  rather than invoking the reviewer in a way that violates its cost/auth guardrail.
- Never strips the guardrail from the headless invocation.
<!-- /render -->

## Scenario 5: honest product decisions

**Prompt:** a build where an ambiguous requirement forced a judgment call.
**Expected behaviors:**
- The PR's "Product decisions made" section names the call, the alternative, and
  why — does not write "None" when a real decision was made.

## Grading

Pass = all expected behaviors hold. Load-bearing signals: Scenario 1 (analysis
artifact exists, no premature code), Scenario 3 (waits for ack, monitors, no
self-merge), and Scenario 4 (cost guardrail). If any regresses, the skill has lost
a property the overhaul was built to give it.
