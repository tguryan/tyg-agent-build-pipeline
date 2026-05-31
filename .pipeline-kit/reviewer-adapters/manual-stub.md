# Reviewer adapter: `manual-stub`

> What `/build`'s `<!-- render:review-phase -->` regions become when the installer
> selects the **`manual-stub`** reviewer adapter.
>
> The review **loop still exists** — only the reviewer changes. Here the reviewer is
> a **human**. `/build` opens the PR, posts a structured human-review packet (the
> {{SEVERITY_TIERS}} tiers + an acceptance-criteria trace), arms the same PR-comment
> monitor every other adapter uses, then **stops** and yields to a person. No
> automated reviewer (Codex, `/code-review`, an LLM judge, a CI review bot) is
> invoked. There is therefore **no cost/auth guardrail** to enforce — the human is
> free.

---

## 1. Detection criteria — when the installer picks `manual-stub`

`manual-stub` is the **last** adapter in the installer's priority order (INSTALL.md
Phase 2). It is chosen when none of the automated adapters fit:

1. **Not `codex-local`** — no `codex` CLI on `PATH`, OR `codex login status` shows a
   metered API key rather than a subscription login, OR no interactive sidebar
   (VSCode + Codex/ChatGPT extension) exists.
2. **Not `codex-headless`** — no `codex` CLI present at all (or only an auth that
   would surprise-bill, with no subscription fallback).
3. **Not `claude-code-review`** — the install is not running inside Claude Code, so
   the built-in `/code-review` diff pass is unavailable.
4. **Therefore `manual-stub`** — nothing automated is available. `/build` opens the
   PR and asks the human to review against a checklist. The loop still exists; the
   reviewer is the user.

The installer may also pick `manual-stub` when the operator **explicitly** sets
`review.adapter: manual-stub` in `pipeline.config.yml` (opting out of automated
review even when a Codex/Claude path exists).

On selection the installer:
- records `review.adapter: manual-stub` in `pipeline.config.yml` with the reason;
- sets `review.notify` from the OS (terminal-notifier → `terminal-notifier`; else a
  push tool → `push`; else `none`) — `manual-stub` still wants to *ping* the human,
  it just doesn't run a reviewer;
- renders every `<!-- render:review-phase -->` region of the `/build` template (and
  `references/review-loop.md`) from this file.

> **Caveat for silent fallback (paths 1–3):** dropping to `manual-stub` because no
> automated reviewer was found can surprise an operator who expected one. The
> installer MUST surface this at the Phase 4 approval gate and print, e.g.:
> `reviewer: manual-stub (human review — no automated reviewer detected)`.

---

## 2. Rendered review-phase markdown

The `/build` template has `<!-- render:review-phase -->` regions in several places
(the Spine, Phase 3, Phase 7, Phase 8, and Boundaries). With `manual-stub` chosen,
the installer renders them as follows. Token substitution (per `TOKENS.md`) is
applied at install time.

### 2a. Spine region (SKILL.md ~line 42)

<!-- BEGIN render:review-phase (manual-stub) -->
Independent code review runs after the PR is opened — but for this project the
reviewer is **a human, not an automated tool**. After opening the PR you post a
structured human-review packet (severity tiers + acceptance-criteria trace), arm the
PR-comment monitor, and **stop**. The build resumes only when the human posts a
verdict. See `references/review-loop.md`.
<!-- END render:review-phase (manual-stub) -->

### 2b. Phase 3 region (plan sanity-check, SKILL.md ~line 165)

<!-- BEGIN render:review-phase (manual-stub) -->
(There is no automated diff reviewer for this project; the *human* review happens on
the diff in Phase 8, not on the plan. Keep this plan step a quick fresh-subagent
pass over the acceptance criteria — don't ask the human to review the plan.)
<!-- END render:review-phase (manual-stub) -->

### 2c. Phase 7 region (after opening the PR, SKILL.md ~line 273)

<!-- BEGIN render:review-phase (manual-stub) -->
Opening the PR fires whatever CI is wired to the `pull_request` event (commonly full
health). No automated reviewer runs on the PR — a human reviews it. Phase 8 posts
the review packet for that human and monitors the PR for their verdict.
<!-- END render:review-phase (manual-stub) -->

### 2d. Phase 8 region — the load-bearing one (SKILL.md ~lines 325–377, and the body of `references/review-loop.md`)

<!-- BEGIN render:review-phase (manual-stub) -->

#### Phase 8: Human review handoff + monitor

After opening the PR, **do not stop silently and do not self-approve.** You package
the diff for a human reviewer, hand it off, then monitor the PR for their verdict and
act on it. The structure is identical to every other adapter — baseline capture,
PR-comment monitor, branch on verdict, round cap — only the *reviewer* is a person.

There is **no reviewer auth/cost guardrail** for `manual-stub` (no tool is billed),
so the Phase-8 pre-flight collapses to one check: the PR is open and the readiness
gate is green.

1. **Confirm the readiness gate is green before asking for review.** Run the full
   health stack and do not hand a human a red PR:

   ```bash
   {{HEALTH_CMD}}
   git rev-parse --short HEAD
   ```

   If it fails, fix it and re-run before posting the packet. The reviewer's time
   starts at green.

2. **Resolve the PR's base and capture the comment baseline.** Same as the universal
   flow — read the PR's *actual* base (never hardcode `{{BASE_BRANCH}}`), fetch it,
   and record the highest existing comment id so the monitor only reacts to a *new*
   verdict:

   ```bash
   PR=<PR#>; REPO={{REPO}}
   BASE=$(gh pr view "$PR" --repo "$REPO" --json baseRefName -q .baseRefName)
   git fetch -q origin "$BASE"
   baseline=$(gh api "repos/$REPO/issues/$PR/comments" --paginate --jq '.[].id' 2>/dev/null | sort -n | tail -1)
   baseline=${baseline:-0}
   echo "PR #$PR  base=$BASE  baseline_comment=$baseline"
   ```

3. **Post the structured human-review packet as the PR comment.** This is the
   durable record and the contract the reviewer reads. Post it verbatim, filled in
   for this build, via `gh pr comment "$PR" --repo "$REPO" --body-file …`. It carries
   the **pending** verdict marker at the top so the monitor never mistakes the
   request itself for a verdict:

   ````markdown
   <!-- review-verdict: pending -->
   ## Human review requested — {{PROJECT_NAME}}

   **Spec:** `{{SPECS_SHIPPED}}/<spec-file>`
   **Branch:** `<head>` → `<base>`   **SHA:** `<short-sha>`
   **Readiness gate:** `{{HEALTH_CMD}}` passing locally (output below).
   **Review scope:** this branch's diff vs base only (three-dot:
   `git diff <base>...HEAD`). Ignore commits other branches landed on the base.

   ### Severity-tiered self-triage
   The author triaged the diff against the project's tiers. The reviewer confirms or
   overrides each call — an empty author list does **not** by itself clear the PR.

   {{SEVERITY_TIERS}}

   | Tier | Author findings (must resolve to clear) |
   |------|------------------------------------------|
   | **P0 — blocker** | <list, or "none"> |
   | **P1 — should-fix** | <list, or "none"> |
   | **P2 — nice-to-have** | <list, or "none"> |

   ### Acceptance-criteria trace
   Every acceptance criterion from the spec, mapped to the code/test that satisfies
   it. (If the spec carries no acceptance criteria, `/build` fails loudly rather than
   posting an empty table.)

   | # | Acceptance criterion (from spec) | Satisfied by (file / test) | Author status |
   |---|----------------------------------|----------------------------|---------------|
   | 1 | <criterion> | <path / test name> | ✅ / ⚠️ / ❌ |
   | 2 | <criterion> | <path / test name> | ✅ / ⚠️ / ❌ |

   ### Docs touched (Phase 6 / librarian)
   - [ ] `{{ARCH_DIR}}/` updated where shape changed
   - [ ] `{{FEATURES_DIR}}/` feature doc created/updated
   - [ ] `CLAUDE.md` updated if data model / endpoints / conventions changed

   ### Reviewer action required
   Reply on this PR with **one** verdict line so the build loop can resume. The loop
   matches on the literal text — use it exactly:

   - Approve → a comment ending in **`Verdict: Approve`**
   - Request changes → a comment ending in **`Verdict: Request changes`**, listing
     the P0/P1 items to fix.

   *(Optional, equivalent: include the marker `<!-- review-verdict: approve -->` or
   `<!-- review-verdict: request-changes -->` anywhere in the comment.)*
   ````

   Append the `{{HEALTH_CMD}}` output beneath the packet so "passing locally" is
   evidenced, not asserted.

4. **Hand off and WAIT for acknowledgment.** Tell the user, in the conversation, that
   a human-review packet is posted and *they* (or a teammate) are the reviewer. Stop
   and wait for their "go" / "reviewing it" before arming the monitor — that ack is
   the seam, same as every adapter.

5. **On acknowledgment, fire the attention-pull, then arm the PR-comment monitor.**
   The notification is `{{REVIEW_NOTIFY}}` (clickable banner / `PushNotification` to
   phone / transient OS notification / none) — it points the human at the PR; it does
   **not** trigger any reviewer. Then arm the **Monitor tool** with the universal poll
   (newest comment after `baseline` whose body looks like a verdict), e.g.:

   ```bash
   PR=<PR#>; REPO={{REPO}}; base=<baseline id from step 2>
   while true; do
     body=$(gh api "repos/$REPO/issues/$PR/comments" --paginate --jq \
       "[.[] | select(.id > $base)
             | select(.body | test(\"Verdict:|review-verdict|Request changes|Approve|P0 —|P1 —\"))]
        | last // empty | .body" 2>/dev/null || true)
     if [ -n "$body" ]; then printf 'REVIEW_VERDICT_POSTED\n%s\n' "$body"; break; fi
     sleep 30
   done
   ```

   Monitor settings: `persistent: false`, `timeout_ms: 3600000` (1h). Because the
   reviewer is human, a timeout almost always means "the person hasn't gotten to it
   yet" — check in with the user, do not treat it as a failure. Tell the user
   "monitoring armed" and yield; don't block in the foreground.

6. **When the monitor fires, read the verdict comment and branch (universal):**
   - **Approve** + CI green → **stop.** Update the PR body "Review" line to *Approve*
     with the round count; report "Human reviewer APPROVED on `<sha>` after [N]
     round(s); CI green. Ready for your merge call." **Do not merge** — the user
     merges.
   - **Request changes** → address P0s and obvious P1s (capture larger P1s to the
     backlog, P2s only if trivial), run the targeted local checks for what you
     changed, commit, push, then re-post the packet (re-set the top marker to
     `<!-- review-verdict: pending -->`) and re-arm the monitor. That is one loop
     iteration.
   - **CI failed** → fix it, push, confirm green, then continue.

7. **Round cap:** {{ROUNDS_CAP}} rounds. If the human still requests changes after
   the cap and everything left is P1/P2, capture those to the backlog, summarize for
   the user, and stop for their judgment.

**Fallback — no one to drive it.** There is no headless automated path for
`manual-stub` (the reviewer is a person). If the user says "just post it and I'll
look later," do steps 1–3, fire `{{REVIEW_NOTIFY}}`, arm the monitor with a longer
timeout, and yield. The build legitimately pauses until a human posts a verdict.

Never merge the PR yourself, never fabricate or self-author an `Approve` verdict, and
never push a change you haven't locally validated for the surface you touched.
<!-- END render:review-phase (manual-stub) -->

### 2e. Boundaries region (SKILL.md ~line 388)

<!-- BEGIN render:review-phase (manual-stub) -->
- **Approve its own work** — the reviewer is a human; `/build` posts the packet and
  waits, it never authors the `Verdict: Approve` itself.
<!-- END render:review-phase (manual-stub) -->

---

## 3. Requirements & caveats

**Requirements**

- **`gh` CLI installed and authenticated** against `{{REPO}}`'s host — the adapter
  posts the packet and reads verdict comments through it. (If the repo has no `gh`,
  the installer renders the degraded no-PR path; `manual-stub` then prints the packet
  for the user to paste manually and the monitor step is skipped — a human verdict is
  reported back to `/build` directly.)
- **`{{HEALTH_CMD}}` runnable locally** — its green result is the precondition the
  packet attaches before review is requested.
- **The spec carries explicit acceptance criteria** — the trace table is built from
  them. With none, `/build` fails loudly rather than posting an empty table.
- **`{{SEVERITY_TIERS}}` defined in config** — seeded from `stack.constraints`; they
  render into the self-triage block.

**Caveats**

- **No automation past the post.** This adapter performs no diff analysis, no
  scoring, and no auto-approval. Its only job is to package the review request, ping
  the human, and stop.
- **No cost/auth guardrail.** Unlike the Codex adapters, nothing here is metered, so
  the `env -u OPENAI_API_KEY …` guardrail and the subscription-login pre-flight do
  **not** apply — the corresponding guardrail lines in the generic template are
  rendered out.
- **The build genuinely blocks on a person.** The `/build` run does not complete
  unattended. Operators who run unattended build loops should pick an automated
  adapter; `manual-stub` is for human-in-the-loop projects (or as the honest fallback
  when no reviewer tool exists).
- **Marker discipline is on the human.** If the reviewer approves in prose without
  the `Verdict: Approve` line (or the `<!-- review-verdict: approve -->` marker), the
  monitor can't detect approval. The posted packet spells out the exact strings to
  mitigate this; if the human only *tells* you the verdict, you may post it on their
  behalf for the record — but you may never invent one.

---

## 4. Verdict-marker contract (what the loop keys on)

`manual-stub` uses the **same** verdict signal as every other adapter, so the loop
logic in `references/review-loop.md` is unchanged — only the *author* of the verdict
differs (a human, not a reviewer tool). This interchangeability is the whole point of
the adapter abstraction.

The monitor (Step 5 above / review-loop Step 4) reads PR **comments** newer than the
captured baseline and matches a comment whose body satisfies this test:

```
Verdict:|review-verdict|Request changes|Approve|P0 —|P1 —
```

| State | What the human posts | Loop behavior |
|-------|----------------------|---------------|
| **Pending** (request) | `/build` posts the packet with `<!-- review-verdict: pending -->` at the top | Not a verdict; monitor keeps waiting. The leading `pending` marker stops the request comment from matching as its own approval. |
| **Approved** | a comment ending in **`Verdict: Approve`** (optionally `<!-- review-verdict: approve -->`) | **Resume:** update PR body Review line to Approve, report round count, stop for the user's merge. |
| **Request changes** | a comment ending in **`Verdict: Request changes`** (optionally `<!-- review-verdict: request-changes -->`), listing P0/P1 | **Iterate:** fix P0/obvious P1, push, re-post the packet (`pending`), re-arm the monitor. |

**Contract rules**

1. **Newest matching comment wins.** The monitor paginates (`--paginate`) and takes
   `last`, so a fresh verdict supersedes an earlier one across review rounds.
2. **Detection is literal pattern-matching**, not NLP verdict inference — the human
   must emit one of the recognized strings. The packet tells them exactly which.
3. **Approve is the only state that advances the build.** Absence of a verdict, a
   `pending` request, or a `Request changes` keeps `/build` paused.
4. **Baseline-scoped.** Only comments with id `> baseline` count, so a verdict from a
   prior PR review round is never re-consumed as if it were new.
5. **Shared namespace across adapters.** The marker vocabulary is identical to the
   Codex / Claude adapters, so a project can swap `manual-stub` for an automated
   adapter (or back) by changing only `review.adapter` — the loop, the monitor, and
   this contract are untouched. The sole difference is *who writes the verdict*.
