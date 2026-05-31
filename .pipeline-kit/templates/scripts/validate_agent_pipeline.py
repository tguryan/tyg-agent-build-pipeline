#!/usr/bin/env python3
"""Validate {{PROJECT_NAME}} agent/skill routing invariants.

Portable pipeline contract validator. Checks that the skills declared in the
pipeline config are actually present, that the canonical skills manifest and
CLAUDE.md agree with what is on disk, that spec directories exist, and (when a
cross-tool mirror is enabled) that .agents/skills/ is a faithful copy of
.claude/skills/.

The set of skills it enforces is read from the pipeline config's
`skills.enabled` list — there is no hardcoded skill list. Drop the config in
and this validator adapts to whatever pipeline the repo installed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
AGENTS_SKILLS = ROOT / ".agents" / "skills"
MANIFEST = CLAUDE_SKILLS / "README.md"
PIPELINE_CONFIG = ROOT / ".pipeline-kit" / "pipeline.config.yml"

# Spec directories the pipeline reads/writes. Resolved from config tokens at
# install time. Empty values are skipped (e.g. a repo with no reviews dir).
SPEC_DIRS = [
    "{{SPECS_DRAFT}}",
    "{{SPECS_SHIPPED}}",
    "{{SPECS_REVIEWS}}",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def enabled_skills() -> tuple[list[str], str | None]:
    """Read skills.enabled from the pipeline config.

    Returns (skills, error). Parsed with a small dependency-free YAML-ish
    reader so the validator has no third-party requirements. Supports both
    inline `enabled: [a, b]` and block list form.
    """
    if not PIPELINE_CONFIG.exists():
        return [], f"Missing pipeline config: {rel(PIPELINE_CONFIG)}"

    text = read(PIPELINE_CONFIG)
    lines = text.splitlines()

    in_skills = False
    skills_indent = 0
    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(raw) - len(raw.lstrip())

        # Top-level `skills:` block opener.
        if not in_skills:
            if stripped.rstrip(":") == "skills" and stripped.endswith(":"):
                in_skills = True
                skills_indent = indent
            continue

        # We are inside the skills block; a key at or below its indent ends it.
        if indent <= skills_indent:
            break

        key, _, value = stripped.partition(":")
        if key.strip() != "enabled":
            continue

        value = value.strip()
        # Inline form: enabled: [lifepm, spec, build]   # optional trailing comment
        if value.startswith("["):
            # slice between the first '[' and the LAST ']' so a trailing
            # `# {{TOKEN}}` annotation after the bracket can't corrupt the final item
            rb = value.rfind("]")
            inner = value[1:rb] if rb != -1 else value[1:]
            items = [item.strip().strip("'\"") for item in inner.split(",")]
            return [item for item in items if item], None

        # Block form: enabled:\n  - lifepm\n  - spec
        items = []
        for follow in lines[idx + 1 :]:
            fstripped = follow.strip()
            if not fstripped or fstripped.startswith("#"):
                continue
            findent = len(follow) - len(follow.lstrip())
            if not fstripped.startswith("-") or findent <= indent:
                break
            items.append(fstripped.lstrip("-").strip().strip("'\""))
        return [item for item in items if item], None

    return [], f"No skills.enabled list found in {rel(PIPELINE_CONFIG)}"


def parse_manifest() -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in read(MANIFEST).splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0] in {"Skill", "---"}:
            continue
        path_match = re.search(r"`([^`]+)`", cells[1])
        if path_match:
            rows[cells[0]] = path_match.group(1)
    return rows


def skill_entrypoints(base: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        files_by_exact_name = {
            path.name: path for path in child.iterdir() if path.is_file()
        }
        existing = [
            files_by_exact_name[name]
            for name in ("SKILL.md", "skill.md")
            if name in files_by_exact_name
        ]
        if len(existing) == 1:
            entries[child.name] = existing[0].relative_to(base).as_posix()
        elif len(existing) > 1:
            entries[child.name] = "MULTIPLE"
        else:
            entries[child.name] = "MISSING"
    return entries


def collect_files(base: Path) -> dict[str, Path]:
    if not base.exists():
        return {}
    return {
        path.relative_to(base).as_posix(): path
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def ignored_by_git(paths: list[Path]) -> list[str]:
    if not paths or not (ROOT / ".git").exists():
        return []

    rel_paths = [rel(path) for path in paths]
    try:
        result = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            input="\n".join(rel_paths) + "\n",
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return []

    if result.returncode not in {0, 1}:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def validate() -> list[str]:
    errors: list[str] = []

    if not CLAUDE_SKILLS.is_dir():
        return [f"Missing skills directory: {rel(CLAUDE_SKILLS)}"]

    if not MANIFEST.exists():
        return [f"Missing skills manifest: {rel(MANIFEST)}"]

    # Skills declared in the pipeline config — the source of truth for what
    # this repo's pipeline should ship. Validated against manifest + disk.
    configured, config_err = enabled_skills()
    if config_err:
        errors.append(config_err)

    manifest = parse_manifest()
    if not manifest:
        errors.append(f"No skill entries found in {rel(MANIFEST)}")

    for skill, path_text in manifest.items():
        target = CLAUDE_SKILLS / path_text
        if not target.exists():
            errors.append(
                f"Manifest entry for '{skill}' points to missing file: {rel(target)}"
            )

    entrypoints = skill_entrypoints(CLAUDE_SKILLS)
    for skill, path_text in entrypoints.items():
        if path_text == "MULTIPLE":
            errors.append(f"Skill '{skill}' has both SKILL.md and skill.md")
        elif path_text == "MISSING":
            errors.append(f"Skill '{skill}' has no SKILL.md or skill.md")
        elif manifest.get(skill) != path_text:
            errors.append(
                f"Skill '{skill}' entrypoint is {path_text}, "
                f"but manifest says {manifest.get(skill)!r}"
            )

    for skill in sorted(set(manifest) - set(entrypoints)):
        errors.append(f"Manifest lists '{skill}', but no matching skill directory exists")

    # Every configured skill must be on disk and in the manifest.
    for skill in sorted(set(configured) - set(entrypoints)):
        errors.append(
            f"Config skills.enabled lists '{skill}', but no matching skill directory exists"
        )
    for skill in sorted(set(configured) - set(manifest)):
        errors.append(
            f"Config skills.enabled lists '{skill}', but the manifest has no matching entry"
        )

    claude_md = ROOT / "CLAUDE.md"
    if claude_md.exists():
        text = read(claude_md)
        section_match = re.search(
            r"## Development Skills(?P<body>.*?)(?:\n## |\Z)",
            text,
            flags=re.S,
        )
        if section_match:
            listed = set(re.findall(r"\| `/([a-z0-9-]+)` \|", section_match.group("body")))
            for skill in sorted(set(manifest) - listed):
                errors.append(f"CLAUDE.md Development Skills omits '/{skill}'")
            for skill in sorted(listed - set(manifest)):
                errors.append(
                    f"CLAUDE.md Development Skills lists '/{skill}', "
                    "but the manifest has no matching skill"
                )

    # Guard against UTF-8 replacement characters leaking into agent-facing docs.
    scan_roots = [
        ROOT / "AGENTS.md",
        ROOT / "CLAUDE.md",
        CLAUDE_SKILLS,
    ]
    for root in scan_roots:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else sorted(root.rglob("*"))
        for path in paths:
            if not path.is_file():
                continue
            text = read(path)
            if "�" in text:
                errors.append(f"Replacement character found in {rel(path)}")

    # Spec directories the pipeline depends on must exist.
    for spec_dir in SPEC_DIRS:
        if not spec_dir or spec_dir.startswith("{{"):
            continue
        target = ROOT / spec_dir
        if not target.is_dir():
            errors.append(f"Missing spec directory: {rel(target)}")

    # Cross-tool mirror: .agents/skills must be a byte-for-byte copy of
    # .claude/skills when the mirror is present.
    if AGENTS_SKILLS.exists():
        claude_files = collect_files(CLAUDE_SKILLS)
        agent_files = collect_files(AGENTS_SKILLS)
        for path_text in sorted(set(claude_files) - set(agent_files)):
            errors.append(f".agents/skills missing mirror file: {path_text}")
        for path_text in sorted(set(agent_files) - set(claude_files)):
            errors.append(f".agents/skills has extra mirror file: {path_text}")
        for path_text in sorted(set(claude_files) & set(agent_files)):
            if claude_files[path_text].read_bytes() != agent_files[path_text].read_bytes():
                errors.append(f".agents/skills mirror drift: {path_text}")
        for path_text in ignored_by_git(list(agent_files.values())):
            errors.append(f".agents/skills mirror file is ignored by git: {path_text}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Agent pipeline validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Agent pipeline validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
