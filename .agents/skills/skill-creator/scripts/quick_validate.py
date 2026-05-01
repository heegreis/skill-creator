#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""
Quick validation script for skills.

Validates SKILL.md frontmatter and (with --strict) also checks body length,
referenced file existence, and section structure.

Usage:
    python scripts/quick_validate.py <skill_directory>
    python scripts/quick_validate.py <skill_directory> --strict

    uv run scripts/quick_validate.py <skill_directory> --strict

Examples:
    python scripts/quick_validate.py .agents/skills/my-skill
    python scripts/quick_validate.py .agents/skills/my-skill --strict
"""

import argparse
import re
import sys
import yaml
from pathlib import Path


# ---------------------------------------------------------------------------
# Frontmatter validation (always runs)
# ---------------------------------------------------------------------------

def validate_frontmatter(skill_path: Path, content: str) -> list[tuple[str, str]]:
    """Validate SKILL.md frontmatter.  Returns list of (level, message) tuples.

    Level is "error" (blocks --strict) or "warning" (advisory).
    """
    issues: list[tuple[str, str]] = []

    if not content.startswith("---"):
        issues.append(("error", "No YAML frontmatter found (file must start with ---)"))
        return issues

    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        issues.append(("error", "Invalid frontmatter format (no closing ---)"))
        return issues

    frontmatter_text = match.group(1)

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        if not isinstance(frontmatter, dict):
            issues.append(("error", "Frontmatter must be a YAML dictionary"))
            return issues
    except yaml.YAMLError as e:
        issues.append(("error", f"Invalid YAML in frontmatter: {e}"))
        return issues

    ALLOWED_PROPERTIES = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
    unexpected_keys = set(frontmatter.keys()) - ALLOWED_PROPERTIES
    if unexpected_keys:
        issues.append((
            "error",
            f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected_keys))}. "
            f"Allowed properties are: {', '.join(sorted(ALLOWED_PROPERTIES))}",
        ))

    if "name" not in frontmatter:
        issues.append(("error", "Missing 'name' in frontmatter"))
    else:
        name = frontmatter["name"]
        if not isinstance(name, str):
            issues.append(("error", f"Name must be a string, got {type(name).__name__}"))
        else:
            name = name.strip()
            if not re.match(r"^[a-z0-9-]+$", name):
                issues.append(("error", f"Name '{name}' should be kebab-case (lowercase letters, digits, hyphens only)"))
            elif name.startswith("-") or name.endswith("-") or "--" in name:
                issues.append(("error", f"Name '{name}' cannot start/end with hyphen or contain consecutive hyphens"))
            elif len(name) > 64:
                issues.append(("error", f"Name is too long ({len(name)} chars). Maximum is 64."))

    if "description" not in frontmatter:
        issues.append(("error", "Missing 'description' in frontmatter"))
    else:
        desc = frontmatter["description"]
        if not isinstance(desc, str):
            issues.append(("error", f"Description must be a string, got {type(desc).__name__}"))
        else:
            desc = desc.strip()
            if "<" in desc or ">" in desc:
                issues.append(("error", "Description cannot contain angle brackets (< or >)"))
            if len(desc) > 1024:
                issues.append(("error", f"Description is too long ({len(desc)} chars). Maximum is 1024."))

    compatibility = frontmatter.get("compatibility", "")
    if compatibility:
        if not isinstance(compatibility, str):
            issues.append(("error", f"Compatibility must be a string, got {type(compatibility).__name__}"))
        elif len(compatibility) > 500:
            issues.append(("error", f"Compatibility is too long ({len(compatibility)} chars). Maximum is 500."))

    return issues


# ---------------------------------------------------------------------------
# Body lint (always runs, --strict upgrades warnings to errors)
# ---------------------------------------------------------------------------

def lint_body(skill_path: Path, content: str) -> list[tuple[str, str]]:
    """Check the SKILL.md body (below frontmatter) for common issues.

    Returns list of (level, message) tuples where level is "warning".
    """
    issues: list[tuple[str, str]] = []

    # Locate body start (after closing ---)
    fm_end = content.find("\n---\n", 3)
    if fm_end == -1:
        return issues  # Already caught by frontmatter validator
    body = content[fm_end + 5:]  # skip "\n---\n"

    # Line count
    body_lines = body.splitlines()
    if len(body_lines) > 500:
        issues.append((
            "warning",
            f"SKILL.md body is {len(body_lines)} lines (> 500). "
            "Consider moving sections to references/ to keep context usage low.",
        ))

    # Token estimate (rough: chars / 4)
    token_estimate = len(body) // 4
    if token_estimate > 5000:
        issues.append((
            "warning",
            f"SKILL.md body is ~{token_estimate} tokens (> 5000). "
            "This may consume significant context on every invocation.",
        ))

    # Section headers
    headers = [l for l in body_lines if l.startswith("## ")]
    if not headers:
        issues.append((
            "warning",
            "SKILL.md body has no ## headers. "
            "Adding section headers improves progressive disclosure.",
        ))

    # Referenced scripts/ and references/ paths
    path_refs = re.findall(r"`((?:scripts|references|agents|assets)/[^`\s]+)`", content)
    for ref in path_refs:
        ref_path = skill_path / ref
        if not ref_path.exists():
            issues.append((
                "warning",
                f"Referenced path does not exist: {ref} (looked at {ref_path})",
            ))

    return issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def validate_skill(skill_path: Path, strict: bool = False) -> tuple[bool, list[str]]:
    """Validate a skill directory.

    Returns (passed, messages) where passed is False if any errors were found
    (or if strict=True and any warnings were found).
    """
    skill_path = Path(skill_path)
    messages: list[str] = []

    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return False, [f"Error: SKILL.md not found at {skill_md}"]

    content = skill_md.read_text(encoding="utf-8", errors="replace")

    issues: list[tuple[str, str]] = []
    issues.extend(validate_frontmatter(skill_path, content))
    issues.extend(lint_body(skill_path, content))

    has_error = False
    for level, msg in issues:
        if level == "error":
            messages.append(f"Error: {msg}")
            has_error = True
        else:
            messages.append(f"Warning: {msg}")
            if strict:
                has_error = True

    if not has_error:
        messages.append("Skill is valid!")

    return not has_error, messages


def main():
    parser = argparse.ArgumentParser(
        description="Validate a skill directory's SKILL.md",
        epilog=(
            "Examples:\n"
            "  python scripts/quick_validate.py .agents/skills/my-skill\n"
            "  python scripts/quick_validate.py .agents/skills/my-skill --strict\n"
            "  uv run scripts/quick_validate.py .agents/skills/my-skill --strict\n"
            "\nExit codes: 0 = valid, 1 = invalid."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("skill_dir", help="Path to the skill directory")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (body too long, missing headers, broken refs)",
    )
    args = parser.parse_args()

    skill_path = Path(args.skill_dir)
    if not skill_path.exists():
        print(
            f"Error: Skill directory not found — got: {args.skill_dir}. "
            f"Try: check the path points to a valid skill directory.",
            file=sys.stderr,
        )
        sys.exit(1)

    passed, messages = validate_skill(skill_path, strict=args.strict)
    for msg in messages:
        print(msg)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
