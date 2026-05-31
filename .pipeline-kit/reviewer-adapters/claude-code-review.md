# Reviewer adapter: `claude-code-review`

Independent diff review using Claude Code's built-in `/code-review` skill instead
of an external reviewer. No OpenAI Codex, no ChatGPT auth, no metered API, no
external billing. The review runs in-process against the working-tree / PR diff,
findings are captured, fixed, and re-reviewed in a loop until clean.

This file defines what `/build`'s `<!-- render:review-phase --> … <!-- /render -->`
region becomes when the installer selects this adapter. The installer copies the
rendered markdown block (Section 2) verbatim into the built `build/SKILL.md`,
resolving every `{{TOKEN}}` from `pipeline.config.yml`.

---

## 1. Detection criteria (when the installer picks this)

The installer chooses adapters in priority order. It selects `claude-code-review`
when **all** of the following hold:

1. **No usable Codex.** The `codex` CLI is absent from `PATH`, OR present but not
   authenticated (no ChatGPT/subscription session), OR the user explicitly opted
   out of external reviewers. This rules out `codex-local` and `codex-headless`.
2. **Claude Code's `/code-review` is available.** The host is Claude Code (or an
   environment exposing the built-in `code-review` skill). The installer confirms
   by checking the skill registry for a `code-review` entry.
3. **The user has not requested `manual-stub`.** `manual-stub` is the last-resort
   fallback when no programmatic reviewer exists at all; if `/code-review` is
   present, prefer it over a human-only stub.

Set in config when chosen:

```yaml
review:
  adapter: "claude-code-review"
```

If `codex` IS available and authed, the installer prefers a `codex-*` adapter
(independent model = stronger second opinion). `claude-code-review` is the
best self-contained option: zero external dependencies, zero billing, same-model
but genuinely independent pass (fresh context, adversarial diff read).

---

## 2. Rendered review-phase markdown

> The installer substitutes this entire block for the `<!-- render:review-phase -->`
> region in `build/SKILL.md`. Tokens resolve from `pipeline.config.yml`.

<!-- render:review-phase -->
### Phase 8 — Independent review loop (Claude Code `/code-review`)

After the PR is open and `{{HEALTH_CMD}}` is green, run an independent review of
the diff with Claude Code's built-in **`/code-review`** skill. This is a fresh,
adversarial read of the change — not the implementing context — and it is the
gate the build loop keys on. **No external reviewer, no `codex`, no ChatGPT auth,
no metered API, no external billing.** This adapter is the self-contained review
path: it runs entirely inside Claude Code.

**8.0 — Resolve the PR base, capture the baseline.**

Read the PR's *actual* base branch (`gh pr view --json baseRefName` — never
hardcode `{{BASE_BRANCH}}`) and `git fetch` it, so the review anchors on a current
`origin/<base>`. Capture the id of the latest PR comment as a baseline so the loop
can tell a new verdict from old chatter. (For `pr_via_gh: false` repos, skip the
comment baseline; the verdict is written to a file per 8.4.)

**8.1 — Run the review.**

Invoke the built-in skill against the PR diff at high effort:

```
/code-review high --comment
```

- Effort is `high` by default so coverage is broad (it may surface uncertain
  findings — triage them, don't auto-trust). Drop to `medium` for tiny diffs;
  escalate to `max`/`ultra` for risky or large surfaces.
- `--comment` posts findings as inline review comments on the open PR so the
  verdict and findings live with the change. Omit `--comment` for a local-only
  pass on an unpushed branch, then post the verdict comment manually per 8.4.
- Do **not** pass `--fix` on the first pass — read the findings yourself, decide
  what's real, and fix deliberately (see 8.2). `--fix` is acceptable only for a
  batch of unambiguous, low-risk cleanups you've already vetted.
- The review is PR-focused via merge-base (three-dot diff vs the resolved base) —
  other contributors' base-branch commits are excluded.

If `{{REVIEW_NOTIFY}}` is set (e.g. `terminal-notifier` / `push`), fire a banner
when the review completes so the human can glance at the verdict; `none` skips it.
Unlike a sidebar-driven external reviewer, `/code-review` runs in-process — there
is no separate app to hand off to and no acknowledgment to wait for.

Scope the review to the build diff only: the branch's changes against the resolved
base. Ignore pre-existing issues outside the diff (capture them as follow-ups,
don't fix them in this branch).

**8.2 — Triage findings against severity tiers.**

Sort every finding into:

{{SEVERITY_TIERS}}

- **P0 / P1 — must fix before approval.** Correctness bugs, security holes,
  spec violations, broken contracts, anything that breaks the stack constraints
  ({{STACK_CONSTRAINTS}}). Fix these in the working tree, then re-run targeted
  checks for the touched surface plus `{{HEALTH_CMD}}`.
- **P2 — judgment call.** Reuse/simplification/efficiency cleanups and nits. Fix
  the cheap, clearly-correct ones now. Defer the rest: record them in the spec's
  review notes under `{{SPECS_REVIEWS}}` (or as PR follow-up comments) rather than
  expanding scope.

Anything you fix gets committed atomically on the same branch with a message that
names the finding it resolves.

**8.3 — Re-review (the loop).**

After fixing, run `/code-review high` again on the updated diff. Repeat
fix → re-review until the review returns **no P0/P1 findings**, capped at
**{{ROUNDS_CAP}} rounds**. If P0/P1 findings remain after the cap, stop the loop
and escalate to the human with the outstanding findings — do not silently ship
unresolved blockers, and do not chase P2 perfection past the cap.

Each round must keep `{{HEALTH_CMD}}` green. A fix that breaks the health stack is
not done.

**8.4 — Record the verdict (the marker the loop reads).**

The build loop and any CI watcher decide pass/fail by reading a single verdict
marker, not by parsing prose. When the loop converges (no P0/P1, health green),
post or update one PR comment whose body contains exactly one marker line:

```
<!-- review:verdict -->
REVIEW-VERDICT: PASS
reviewer: claude-code-review
rounds: <n>/{{ROUNDS_CAP}}
unresolved: none
```

If the cap is hit with blockers still open, post `FAIL` instead and list them:

```
<!-- review:verdict -->
REVIEW-VERDICT: FAIL
reviewer: claude-code-review
rounds: {{ROUNDS_CAP}}/{{ROUNDS_CAP}}
unresolved:
- P1: <one-line finding>
```

The marker contract is defined in Section 4 of this adapter — emit it byte-for-byte.

<!-- if:has_ui -->
**8.5 — UI diffs.** For changes touching the frontend, the diff review covers
logic only. Pair it with a real-app visual check (the `verify`/`run` flow) before
posting `PASS`; a clean code review does not certify that the UI renders.
<!-- /if -->
<!-- /render -->

---

## 3. Requirements & caveats

**Requires:**
- Claude Code host with the built-in `code-review` skill registered.
- `gh` CLI authenticated (only when `--comment` / PR-comment verdict posting is
  used; for `pr_via_gh: false` repos, fall back to a local verdict file the loop
  reads — see Section 4).
- An open PR (or at minimum a committed branch diffable against `{{BASE_BRANCH}}`).

**Does NOT require:** `codex` CLI, OpenAI/ChatGPT auth, any external API key, any
paid service. This adapter exists precisely to run the pipeline with zero external
reviewer billing.

**Caveats:**
- **Same-model independence.** The reviewer is the same model family as the
  implementer, so it is *independent in context* (fresh read of the diff) but not
  *independent in model*. It catches different bugs than a re-read by the author,
  but it shares blind spots a cross-model reviewer (`codex-*`) would not. If a
  cross-model second opinion is available, prefer a `codex-*` adapter. Treat
  `claude-code-review` as the strong self-contained default, not as equivalent to
  a different model's review.
- **Effort vs. noise.** `high`/`max`/`ultra` widen coverage but raise the false-
  positive rate. Triage every finding against {{SEVERITY_TIERS}} before acting;
  never auto-`--fix` an un-vetted high-effort batch.
- **Diff scoping.** The skill reviews the current diff; keep the branch focused so
  the review stays on the build's changes and doesn't drown in unrelated churn.
- **Loop convergence.** Cap at {{ROUNDS_CAP}} rounds. Capture surviving P2s as
  follow-ups; reviews converge, they don't perfect.

---

## 4. Verdict-marker contract

The build loop (and any CI auto-review watcher) is **marker-driven**: it never
parses review prose. It scans for one HTML-comment sentinel followed by a
`REVIEW-VERDICT:` line, and branches on the value.

**Sentinel + fields (exact):**

```
<!-- review:verdict -->
REVIEW-VERDICT: <PASS|FAIL>
reviewer: claude-code-review
rounds: <n>/{{ROUNDS_CAP}}
unresolved: <none | newline list of "P0:/P1: …" items>
```

**Rules the loop relies on:**

1. **Exactly one** `<!-- review:verdict -->` sentinel per PR. To re-review, **edit
   the existing verdict comment in place** — do not post a second one. The watcher
   reads the latest body of the single marker comment.
2. The line immediately after the sentinel MUST start with `REVIEW-VERDICT: ` and
   be either `PASS` or `FAIL`. Anything else = the loop treats it as "not yet
   reviewed" and waits.
3. `PASS` is emitted **only** when: zero P0/P1 findings remain AND `{{HEALTH_CMD}}`
   is green. Otherwise emit `FAIL`.
4. `rounds: n/{{ROUNDS_CAP}}` records loop iterations. On `FAIL` at the cap, the
   loop stops and escalates to the human with the `unresolved:` list.
5. **Transport.** When `pr_via_gh: true`, the marker lives in a PR comment (posted/
   edited via `gh pr comment` / the `--comment` flag). When `pr_via_gh: false`,
   write the same block to `{{SPECS_REVIEWS}}/<spec-slug>.verdict.md`; the loop
   reads the file instead of the PR.

**Marker compatibility.** This is the same `<!-- review:verdict -->` /
`REVIEW-VERDICT:` contract every reviewer adapter emits — only the `reviewer:`
value differs (`claude-code-review` here, `codex-local` / `codex-headless` /
`manual-stub` elsewhere). Keeping the marker identical across adapters is what lets
`/build` swap reviewers without touching loop logic.
