# Reviewer Adapter: `codex-local`

> Renders the `<!-- render:review-phase -->` … `<!-- /render -->` region of the
> `/build` skill when `review.adapter: codex-local` is chosen in
> `pipeline.config.yml`.
>
> This is the **richest** review path: a watchable IDE loop. A clickable
> `terminal-notifier` banner copies a prompt invoking the `{{PROJECT_SLUG}}-pr-review`
> Codex skill and opens the Codex sidebar in VSCode (`vscode://openai.chatgpt/`).
> A human pastes + runs it in the sidebar (watching the review stream), the skill
> posts a verdict to the PR, and a Monitor watches the PR comments for that
> verdict and re-invokes `/build` to act on it. Subscription-billed (ChatGPT
> auth), never the metered OpenAI API.

---

## 1. Detection Criteria — when the installer picks `codex-local`

The installer selects this adapter when **all** of the following hold on the
machine running the pipeline. It is the preferred adapter whenever the full
macOS + VSCode + Codex toolchain is present, because it is the only adapter that
produces the watchable, click-to-run loop.

1. **Platform is macOS.** The clickable banner, `pbcopy`, `open -a`, and
   `osascript` fallback are all macOS-only.
2. **`codex` CLI is installed and authenticated against a ChatGPT subscription.**
   `codex login status` reports `Logged in using ChatGPT`. If `codex` is missing
   (`npm i -g @openai/codex`) or on metered-API auth, this adapter is not
   eligible — fall back to a non-Codex adapter or stop and report.
3. **VSCode + the OpenAI Codex (ChatGPT) extension are installed**, so the
   `vscode://openai.chatgpt/` deep link resolves to the sidebar. Without the
   extension the URL no-ops.
4. **`terminal-notifier` is on `PATH`** (`brew install terminal-notifier`) for
   the clickable banner. If absent, the loop still works via the fallback notify
   chain (`{{REVIEW_NOTIFY}}`: `push` → `PushNotification`, then `osascript`),
   but the banner is the intended experience.
5. **`gh` CLI is available + authed** (`{{PR_VIA_GH}}`) — the loop posts the
   nudge, polls PR comments, and updates the PR body through `gh`.

If macOS or Codex-subscription auth is unavailable, the installer should choose
`codex-headless` (same review, no watching), `claude-code-review`, or
`manual-stub` instead.

---

## 2. Rendered Review-Phase Markdown

When `codex-local` is chosen, the installer replaces the
`<!-- render:review-phase -->` … `<!-- /render -->` region in `build/SKILL.md`
wholesale with the block below. `{{TOKENS}}` resolve from `pipeline.config.yml`.
Codex-specific mechanics (`terminal-notifier`, `vscode://openai.chatgpt/`,
`env -u OPENAI_API_KEY`) are intentionally literal — per `TOKENS.md`, adapter
mechanics are owned by the adapter, not hardcoded into the skill spine.

<!-- BEGIN render:review-phase (adapter=codex-local) -->

### Phase 8 — Codex review loop (watchable IDE handoff)

Hand the diff review to the **Codex sidebar** so it can be watched as it streams,
then monitor the PR for the verdict and act on it. The review runs through the
local `codex` CLI / sidebar, billed against the **ChatGPT subscription** —
flat-rate and rate-limited, NOT the metered per-token OpenAI API.

The review is driven by the purpose-built **`{{PROJECT_SLUG}}-pr-review` Codex
skill** (`.codex/skills/{{PROJECT_SLUG}}-pr-review/SKILL.md`, version-controlled
in the repo). It owns the PR-focused diff scope, `AGENTS.md` grounding +
`{{CONTEXT_ROOT}}/` routing, the severity tiers, and the verdict marker. The
clipboard prompt and the PR nudge both **invoke it by name**, so the review is
consistent however it is triggered.

#### Cost guardrail (read first — load-bearing)

- **Require subscription auth.** `codex login status` must say
  `Logged in using ChatGPT`. Otherwise STOP and report.
- **Strip the API key on any CLI invocation.** Always `env -u OPENAI_API_KEY
  codex …`. The sidebar already uses subscription auth; this rule keeps the
  headless fallback from silently falling back to metered billing.

#### Step 1 — pre-flight

```bash
codex login status        # must be "Logged in using ChatGPT"
which codex || echo "NO_CODEX"
which terminal-notifier || echo "NO_NOTIFIER"   # banner; fall back if absent
```

#### Step 2 — resolve the PR base, post the nudge, capture the baseline

Resolve the PR's **actual** base and fetch it fresh — never hardcode
`{{BASE_BRANCH}}`, never trust a stale local base. The review is PR-focused via
**merge-base (three-dot) semantics**: it reviews only this branch's divergence
from its fork point, so commits other agents land on the base after you branched
are excluded automatically.

```bash
PR=<PR#>; REPO={{REPO}}
BASE=$(gh pr view "$PR" --repo "$REPO" --json baseRefName -q .baseRefName)
HEAD_REF=$(gh pr view "$PR" --repo "$REPO" --json headRefName -q .headRefName)
git fetch -q origin "$BASE"   # so origin/$BASE (the fork-point anchor) is current
# baseline = MAX existing comment id (0 if none). MUST --paginate, or gh returns
# only the first 30 comments and the monitor may consume a stale prior verdict.
baseline=$(gh api "repos/$REPO/issues/$PR/comments" --paginate --jq '.[].id' 2>/dev/null | sort -n | tail -1)
baseline=${baseline:-0}
echo "PR #$PR  head=$HEAD_REF  base=$BASE  baseline_comment=$baseline"
```

Post the nudge — the **durable** record (survives a missed notification):

```bash
gh pr comment "$PR" --repo "$REPO" --body "$(printf '%s\n' \
"**Ready for Codex review.** Open the Codex sidebar and paste the prompt from the" \
"\`/build\` notification, or paste:" \
"" \
"> Use the \`{{PROJECT_SLUG}}-pr-review\` skill to audit PR #$PR ($HEAD_REF → $BASE)," \
"> base \`$BASE\` (bare branch name). Post the verdict here when done." \
"" \
"/build is monitoring this PR for the result.")"
```

Then fire the attention-pull. **Prefer a clickable `terminal-notifier` banner** —
clicking it copies a prompt that **invokes the `{{PROJECT_SLUG}}-pr-review` skill
on this PR** to the clipboard and opens the Codex sidebar in VSCode. The sidebar
is an agentic chat: paste, Enter, and the skill drives the PR-scoped review and
posts the verdict itself. The deep link opens the sidebar but can't auto-submit,
so the paste+Enter is irreducible.

```bash
PROMPT="Use the {{PROJECT_SLUG}}-pr-review skill to audit PR #$PR ($HEAD_REF → $BASE), base $BASE (bare branch name). Review only this branch's diff vs its merge-base with $BASE, then post the verdict + findings to the PR with gh."

terminal-notifier \
  -title "{{PROJECT_NAME}} /build — Review PR #$PR" \
  -message "Click to open Codex sidebar (review prompt copied)" \
  -sound Glass \
  -execute "printf %s \"$PROMPT\" | pbcopy; open -a 'Visual Studio Code' 'vscode://openai.chatgpt/'"
```

Verified working details (don't regress):
- **Scheme is `vscode://openai.chatgpt/`** (publisher.extension), foregrounded
  with `open -a 'Visual Studio Code'`. NOT `vscode://codex/` — that opens the
  standalone Codex.app, not the VSCode sidebar.
- **`terminal-notifier` must be enabled once** in System Settings → Notifications
  → terminal-notifier (Allow + Persistent). A fresh install is muted by default,
  so the first banners silently no-op.
- **Clipboard is a chat prompt, not a CLI command** — the sidebar is agentic
  chat. The prompt names the PR and tells Codex to self-post the verdict.
- **PR-focused via merge-base.** The skill diffs `origin/<base>...HEAD`
  (three-dot). Pass the base as a **bare branch name** (`$BASE`), not
  `origin/$BASE` — the skill qualifies it.

Fallbacks if `terminal-notifier` is absent (per `{{REVIEW_NOTIFY}}`):
1. **`PushNotification` tool** — reaches a phone if Remote Control is on
   (survives walking away), but isn't clickable.
2. `osascript -e 'display notification …'` — transient, easy to miss.

The notification can be missed; the PR nudge comment can't — that's why the
instruction lives in the comment, not just the banner.

#### Step 3 — hand off and WAIT for acknowledgment

Tell the human, in the conversation:

> PR #N is up and I've sent a notification. Open the Codex sidebar (`Cmd+N` for a
> new thread), paste the copied prompt (it invokes the `{{PROJECT_SLUG}}-pr-review`
> skill on this PR) and Enter — you'll see it stream. It posts the verdict to the
> PR when done. Say "go" once it's running and I'll watch the PR for the result.

**Stop here and wait for acknowledgment.** "go" / "running it" is the explicit
trigger for the monitor. Do not arm the monitor before the ack — that's the
intended seam.

#### Step 4 — on acknowledgment, arm the PR-comment Monitor

Use the **Monitor tool** (background; re-invokes `/build` on the event). It polls
every 30s for a comment newer than `$baseline` whose body looks like a verdict,
prints it, and exits:

```bash
PR=<PR#>; REPO={{REPO}}; base=<baseline id from step 2>
while true; do
  body=$(gh api "repos/$REPO/issues/$PR/comments" --paginate --jq \
    "[.[] | select(.id > $base)
          | select(.body | test(\"Verdict:|codex-verdict|Request changes|Approve|P0 —|P1 —\"))]
     | last // empty | .body" 2>/dev/null || true)
  if [ -n "$body" ]; then
    printf 'CODEX_VERDICT_POSTED\n%s\n' "$body"
    break
  fi
  sleep 30
done
```

Monitor settings: `persistent: false`, `timeout_ms: 3600000` (1h). On timeout,
check in with the human rather than assuming failure. Tell them "monitoring
armed" and yield; the Monitor re-invokes you when the verdict lands. Don't block
in the foreground.

#### Step 5 — branch on the verdict

Read the comment the Monitor surfaced (see the verdict-marker contract below).

- **Approve** + CI health green → **stop.** Update the PR body's "Codex review"
  line to Approve with the round count. Report: "Codex APPROVED on `<sha>` after
  [N] round(s); health green. Ready for your merge call." Do NOT merge — the
  human merges.
- **Request changes** → address P0s and obvious P1s; capture larger P1s to
  `{{CONTEXT_ROOT}}/product/backlog.md`; ignore P2s unless trivial (severity
  tiers: {{SEVERITY_TIERS}}). Run the targeted local checks for what changed,
  commit, push, then **re-nudge (Step 2) and re-arm the Monitor (Step 4)**.
- **CI health failed** → fix it, push, confirm green via `{{HEALTH_CMD}}`, then
  continue.

#### Round cap

{{ROUNDS_CAP}} rounds. If Codex still requests changes after the cap and
everything left is P1/P2, capture those to the backlog, summarize, and stop for
the human's judgment.

#### Constraints

- **Never run `gh pr merge` from `/build`.** The gate is the human reading the
  verdict and merging.
- The `{{PROJECT_SLUG}}-pr-review` skill lives in `.codex/skills/`, auto-discovered
  when Codex runs in the repo; a global symlink at
  `~/.codex/skills/{{PROJECT_SLUG}}-pr-review` makes it available everywhere.

<!-- END render:review-phase (adapter=codex-local) -->

---

## 3. Requirements & Caveats

**Hard requirements (all must be present, or the installer picks another adapter):**
- macOS — the whole clickable-banner / `pbcopy` / `open -a` / `osascript` UX is
  macOS-specific.
- `codex` CLI on `PATH`, authenticated via **ChatGPT subscription**
  (`codex login status` → `Logged in using ChatGPT`).
- VSCode + the OpenAI Codex (ChatGPT) extension — the `vscode://openai.chatgpt/`
  deep link opens the sidebar; without the extension it no-ops.
- `terminal-notifier` on `PATH` for the banner and its `-execute` click action.
  Must be enabled once in System Settings → Notifications (Allow + Persistent),
  or the first banners silently no-op.
- `pbcopy` (macOS clipboard) for the copy-prompt action.
- `gh` CLI available + authed for nudge, comment polling, and PR-body updates.

**Cost guardrail (non-negotiable — preserve verbatim):**
- Codex is always invoked as `env -u OPENAI_API_KEY codex …`. Stripping the key
  forces ChatGPT-subscription auth and prevents accidental metered-API billing.
  The installer must NOT "simplify" this `env -u` wrapper away. The headless
  fallback uses the same guardrail (and `--output-last-message <file>` for a
  deterministic verdict read).

**Caveats:**
- **Human-in-the-loop.** Not fully autonomous: a human clicks the banner and runs
  the review in the sidebar. The automation is in the trigger (banner + nudge) and
  the wait (Monitor on PR comments), not the review itself. The deep link can't
  auto-submit, so paste+Enter is irreducible.
- **Verdict lives in a PR comment.** The Monitor scans PR *comments* only; a
  verdict in the PR *body* is ignored.
- **Baseline pagination.** The baseline comment-id query MUST `--paginate`, or on
  a busy PR the monitor can consume a stale prior verdict as new.
- **Single-PR scope.** `PR`, `BASE`, `HEAD_REF`, `baseline`, and the prompt are
  bound per build; the banner and Monitor target exactly that PR.
- **VSCode scheme is exact.** `vscode://openai.chatgpt/`, not `vscode://codex/`.
- **Skill ownership.** `{{PROJECT_SLUG}}-pr-review` is defined in the consumer's
  `.codex/skills/`, not shipped by this adapter; the adapter references it by name.

---

## 4. Verdict-Marker Contract

The loop keys on a verdict the reviewer writes into a **PR comment**. The
`{{PROJECT_SLUG}}-pr-review` skill emits both a human-readable terminal verdict
line and a machine-readable HTML-comment marker:

```
Verdict: Approve
Verdict: Request changes
```
```
<!-- codex-verdict: approve -->
<!-- codex-verdict: request-changes -->
```

- The Monitor's signature regex is
  `Verdict:|codex-verdict|Request changes|Approve|P0 —|P1 —`. A comment matching
  it, with `id > $baseline`, is treated as the verdict; the **last** such comment
  wins (the latest round).
- Exactly one verdict state per review pass: **Approve** or **Request changes**.
- **Approve** + CI health green → the loop terminates; `/build` updates the PR body
  and stops for the human's merge call. `/build` never merges.
- **Request changes** → `/build` parses the comment for P0/P1 findings, fixes,
  pushes, and re-triggers (back to Step 2), up to `{{ROUNDS_CAP}}` rounds.
- The HTML-comment form is invisible in rendered GitHub markdown but reliably
  greppable; it is the canonical machine signal. The `Verdict:` line is the
  human-readable backstop the regex also accepts.
- The Monitor keys off the baseline id + the verdict signature, **not** the
  comment author — so it works whether Codex self-posts or a human pastes the
  verdict for the record.
