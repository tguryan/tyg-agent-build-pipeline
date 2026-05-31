# Token conventions (templating reference)

When abstracting a LifeOS skill into a kit template, replace each LifeOS-specific
string with the `{{TOKEN}}` below. The installer resolves these from
`pipeline.config.yml`. Leave general prose, structure, and skill logic intact —
only the repo-specific bindings become tokens.

| LifeOS-specific source | Token |
|---|---|
| `LifeOS` (the project name) | `{{PROJECT_NAME}}` |
| `lifeos` (slug, in ids/filenames) | `{{PROJECT_SLUG}}` |
| `tguryan/lifeos` (gh repo) | `{{REPO}}` |
| one-line project description | `{{PROJECT_ONELINER}}` |
| `context/dev/specs/draft` | `{{SPECS_DRAFT}}` |
| `context/dev/specs/shipped` | `{{SPECS_SHIPPED}}` |
| `context/dev/specs/reviews` | `{{SPECS_REVIEWS}}` |
| `context/dev/specs/buildready` | (retired — drop; flow is draft→shipped) |
| `context/dev/arch` | `{{ARCH_DIR}}` |
| `context/product/features` | `{{FEATURES_DIR}}` |
| `context/product/productbrief.md` | `{{PRODUCT_BRIEF}}` |
| `context/product/designbrief.md` | `{{DESIGN_BRIEF}}` |
| `context/research` | `{{RESEARCH_DIR}}` |
| `CLAUDE.md` | `CLAUDE.md` (keep — universal) |
| `AGENTS.md` | `AGENTS.md` (keep if referenced) |
| `bash scripts/health.sh` | `{{HEALTH_CMD}}` |
| `cd frontend && npx tsc --noEmit` | `{{TYPECHECK_CMD}}` |
| `ruff check …` / eslint | `{{LINT_CMD}}` |
| `python3 -m pytest tests/` | `{{TEST_CMD}}` |
| the targeted-validation profile table | `{{TARGETED_PROFILES}}` (installer expands) |
| `scripts/validate_agent_contract.py` | `{{CONTRACT_VALIDATOR}}` |
| `bash scripts/sync-agent-skills.sh` | `{{MIRROR_CMD}}` |
| base branch `main` | `{{BASE_BRANCH}}` |
| stack constraints ("No Tailwind/Redux/ORM", FastAPI, sqlite, React 19) | `{{STACK_CONSTRAINTS}}` / `{{STACK_SUMMARY}}` |
| LifeOS data conventions (`archived_at`, `new_id()`, `log_activity()`, `get_db()`, `read_bounded()`) | `{{DATA_CONVENTIONS}}` (a config-supplied block; omit if empty) |
| the P0/P1/P2 severity lists | `{{SEVERITY_TIERS}}` |
| review adapter mechanics (terminal-notifier, vscode://openai.chatgpt/, codex-local loop) | rendered from the chosen `reviewer-adapters/<adapter>.md`, NOT hardcoded |

## Rules

- **Don't tokenize what's universal.** Skill structure, the explore→plan→test-first
  spine, "what NOT to do" sections, the freedom-spectrum framework, eval-driven
  authoring — all stay verbatim. They're the value; they're not LifeOS-specific.
- **UI-conditional content:** wrap frontend-only guidance so the installer can drop
  it when `{{DESIGN_BRIEF}}` is empty. Mark such blocks with an HTML comment:
  `<!-- if:has_ui -->` … `<!-- /if -->`.
- **The /build review phase** must be a clearly delimited region the installer
  replaces wholesale from the chosen adapter — mark it
  `<!-- render:review-phase -->` … `<!-- /render -->`.
- **Frontmatter:** keep `name`, `description`, `kind`, `targets`, `privacy_tier`,
  `version`. Drop `lifeos_id` (DB-mirror artifact, not portable). The description
  stays third-person, verb-led, trigger-rich — just swap the project name token.
- **No unresolved literals:** every LifeOS string becomes a token or universal text.
  Leave zero `LifeOS`/`lifeos`/`context/dev`/`scripts/health.sh` literals behind.
