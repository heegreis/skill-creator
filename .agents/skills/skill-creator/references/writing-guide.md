# Skill Writing Guide

Reference for writing effective SKILL.md files.

---

## Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

---

## Progressive Disclosure

Skills use a three-level loading system:

1. **Metadata** (name + description) — Always in context (~100 words)
2. **SKILL.md body** — In context whenever skill triggers (<500 lines ideal, ~5000 tokens)
3. **Bundled resources** — As needed (unlimited; scripts can execute without loading)

**Key patterns:**

- Keep SKILL.md under 500 lines. If approaching the limit, extract sections to
  `references/` and add clear pointers in SKILL.md.
- Reference bundled files clearly with guidance on when to read them.
- For large reference files (>300 lines), include a table of contents.

**Domain organization**: When a skill supports multiple domains/frameworks,
organize by variant so Claude only loads the relevant reference file:

```
cloud-deploy/
├── SKILL.md (workflow + selection logic)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

---

## Frontmatter Fields

- **name** (required): Kebab-case identifier, ≤ 64 chars
- **description** (required): Trigger condition + what the skill does. ≤ 1024 chars.
  This is the primary trigger mechanism — be specific about when to use it.
  Tip: Claude tends to undertrigger, so descriptions should be slightly "pushy":
  include phrases like "Make sure to use this skill whenever..."
- **compatibility** (optional): Required tools/Python version/OS constraints
- **license**, **allowed-tools**, **metadata**: See quickstart for details

---

## Writing Patterns

**Defining output formats:**

```markdown
## Report structure

ALWAYS use this exact template:

# [Title]

## Executive summary

## Key findings

## Recommendations
```

**Examples:**

```markdown
## Commit message format

**Example 1:**
Input: Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

---

## Writing Style

- Use the **imperative** form: "Extract the names" rather than "Names should be extracted".
- Explain **why** things matter, not just what to do. LLMs respond better to
  reasoned guidance than rigid MUST/NEVER rules.
- Be general: write for a million different inputs, not just your test cases.
- Write a draft, then read it with fresh eyes and improve.

---

## Principle of Lack of Surprise

Skills must not contain malware, exploit code, or any content that could
compromise system security. A skill's intent should match its description.
Do not create misleading skills or skills designed to facilitate unauthorized
access, data exfiltration, or other malicious activities.
