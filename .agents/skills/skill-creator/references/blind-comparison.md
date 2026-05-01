# Blind Comparison

For situations where you want a more rigorous comparison between two versions
of a skill (e.g., the user asks "is the new version actually better?"), there
is a blind comparison system.

## Overview

The basic idea: give two outputs to an independent agent without telling it
which is which, and let it judge quality blind.  Then analyse why the winner
won.

This is optional and most users won't need it.  The human review loop (via
the eval viewer) is usually sufficient.  Use blind comparison when:

- The user explicitly asks for a rigorous A/B comparison.
- You have made a significant change and want to verify it's actually better
  rather than just different.
- User feedback has been ambiguous and you want an objective second opinion.

## Agents

- `agents/comparator.md` — How to do blind A/B comparison between two outputs.
  Feed the comparator two output directories (labelled A and B, not
  "with_skill" / "without_skill") and let it score both on a rubric.

- `agents/analyzer.md` — How to analyse why one version beat another.  Feed
  the analyzer the comparison results and the two skill versions to get
  concrete improvement suggestions.

## Workflow

1. Run the two versions (current and proposed) into separate output directories
   within the workspace — e.g. `eval-0/version_a/outputs/` and
   `eval-0/version_b/outputs/`.

2. Spawn a comparator subagent for each test case:
   ```
   Read agents/comparator.md, then compare:
   - Output A: <workspace>/eval-0/version_a/outputs/
   - Output B: <workspace>/eval-0/version_b/outputs/
   Save results to: <workspace>/eval-0/comparison-1.json
   ```

3. Once all comparisons are done, spawn an analyzer subagent:
   ```
   Read agents/analyzer.md, then analyze why version A won / version B won.
   Comparisons: <workspace>/eval-*/comparison-*.json
   Version A skill: <path-to-version-a-skill>/SKILL.md
   Version B skill: <path-to-version-b-skill>/SKILL.md
   Save analysis to: <workspace>/analysis.json
   ```

4. Read `analysis.json` and incorporate the improvement suggestions into the
   next skill revision.

## Output Schemas

See `references/schemas.md` for the `comparison.json` and `analysis.json`
schemas.
