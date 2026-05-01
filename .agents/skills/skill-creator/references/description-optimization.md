# Description Optimization: Query Generation Guide

This document provides detailed guidance on generating trigger eval queries for
the Description Optimization workflow in `SKILL.md`.

---

## What Makes a Good Eval Query

Queries must be realistic — the kind of thing a Claude Code or Claude.ai user
would actually type. Not abstract, but concrete with specific details:

- File paths and filenames
- Personal context about the user's job or situation  
- Column names, company names, URLs
- A little backstory
- Mix of lowercase, abbreviations, typos, casual speech
- Mix of lengths, focused on edge cases rather than clear-cut cases

**Bad (too abstract):**
```
"Format this data"
"Extract text from PDF"
"Create a chart"
```

**Good (concrete and specific):**
```
"ok so my boss just sent me this xlsx file (its in my downloads, called
something like 'Q4 sales final FINAL v2.xlsx') and she wants me to add
a column that shows the profit margin as a percentage. The revenue is in
column C and costs are in column D i think"
```

---

## Should-Trigger Queries (8–10)

Think about coverage. You want different phrasings of the same intent:

- Some formal, some casual
- Cases where the user doesn't explicitly name the skill or file type but clearly needs it
- Uncommon use cases
- Cases where this skill competes with another skill but should win

---

## Should-Not-Trigger Queries (8–10)

The most valuable negative tests are **near-misses** — queries that share
keywords or concepts with the skill but actually need something different:

- Adjacent domains
- Ambiguous phrasing where a naive keyword match would trigger but shouldn't
- Cases where the query touches on something the skill does, but in a context
  where another tool is more appropriate

**Avoid obviously irrelevant negatives.** "Write a fibonacci function" as a
negative test for a PDF skill is too easy — it doesn't test anything. The
negative cases should be genuinely tricky.

---

## Eval Set Format

Save as a flat JSON array (not the evals.json format):

```json
[
  { "query": "the user prompt", "should_trigger": true },
  { "query": "another prompt", "should_trigger": false }
]
```

---

## Reviewing with the User

Use the HTML template at `assets/eval_review.html`:

1. Read the template
2. Replace `__EVAL_DATA_PLACEHOLDER__` → the JSON array (no quotes — it's a JS variable)
3. Replace `__SKILL_NAME_PLACEHOLDER__` → the skill's name
4. Replace `__SKILL_DESCRIPTION_PLACEHOLDER__` → the current description
5. Write to a temp file and open it:
   - **POSIX**: `open /tmp/eval_review_<name>.html`
   - **Windows (PowerShell)**: `Start-Process "$env:TEMP\eval_review_<name>.html"`
6. The user edits queries, toggles should-trigger, then clicks "Export Eval Set"
7. The file downloads to `~/Downloads/eval_set.json` — check for the most recent version

This review step matters — bad eval queries produce bad descriptions.
