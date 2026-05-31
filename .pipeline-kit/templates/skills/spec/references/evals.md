# /spec evals

Evaluations for the spec skill. Run these when changing the skill to confirm it
still triggers correctly and still produces specs of the right shape. No external
harness needed — run each scenario through a fresh subagent (Agent tool) with the
skill loaded, then grade the output against the expected behaviors with a second
subagent.

## Trigger evals

The description should fire on these (Claude under-triggers — lean toward firing):

**Should fire**
- "write a spec for a recurring-tasks feature"
- "let's spec out calendar conflict detection"
- "turn this pm conversation into a spec"
- "I need a feature spec for archiving projects"
- "design the weekly-review flow as a spec"
- "remediate the harden findings into a spec"

**Should NOT fire**
- "build the recurring-tasks feature" (→ /build)
- "is this feature idea any good?" (→ /pm)
- "fix the failing calendar test" (→ just fix it)
- "audit the codebase for quality issues" (→ /harden)

## Scenario 1: holds the line on technical design

**Prompt:** "Write a spec for letting users pin a task to the top of a project."
**Inputs:** repo at current state.
**Expected behaviors:**
- Produces Problem, Requirements, Acceptance Criteria, Scope.
- Acceptance criteria are observable/testable (no "works correctly").
- Approach & Constraints is thin: names an analogous existing feature, states
  constraints — does NOT specify a column type, endpoint shape, or migration SQL.
- Does not contain a data-model table or an API contract.
- Runs the inline blind-review pass via a fresh subagent and reports findings count.

## Scenario 2: scales down for a small enhancement

**Prompt:** "Spec adding an 'archived' filter toggle to the projects list."
**Expected behaviors:**
- Recognizes this as a small enhancement: Problem + Requirements (+ criteria),
  and explicitly skips Layer 2 ceremony.
- Does not invent a multi-section spec for a one-line change.

## Scenario 3: catches its own gaps in review

**Prompt:** "Spec a feature that bulk-deletes completed tasks." (Trap: the
project never hard-deletes.)
**Expected behaviors:**
- Either the draft or the inline review flags the conflict with the soft-delete
  convention as a BLOCK/WARN.
- Reconciles toward archive, not delete — or surfaces it to the user as a product
  decision rather than silently speccing a hard delete.

## Grading

A scenario passes if all its expected behaviors hold. The most important signals:
Scenario 1 (no technical design leaks into the spec) and Scenario 3 (the inline
review actually catches a convention violation). If those two regress, the skill
has lost its core value.
