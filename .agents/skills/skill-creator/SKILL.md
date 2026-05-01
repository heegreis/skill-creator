---
name: skill-creator
description: Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
compatibility: >
  Requires Python 3.10+. Optional: uv for self-contained script execution.
  The trigger eval loop (run_loop.py / run_eval.py) requires the claude CLI
  (Claude Code). The eval viewer needs a browser; in headless environments
  use --static. See references/environments.md for platform-specific guidance.
---

# Skill Creator

A skill for creating new skills and iteratively improving them.

At a high level, the process:

- Decide what the skill should do
- Write a draft
- Create 2-3 test prompts and run claude-with-access-to-the-skill on them
- Evaluate results (qualitatively via the viewer, quantitatively via benchmark)
- Rewrite based on feedback and benchmarks
- Repeat until satisfied, then optionally optimize the description and package

Your job is to figure out where the user is in this process and jump in. If they say "I want to make a skill for X", help narrow it down, write the draft, run tests, and iterate. If they already have a draft, go straight to the eval/iterate loop. If they say "just vibe with me", skip the formal evals.

After the skill is done, you can run the description optimizer to improve triggering accuracy.

## Communicating with the user

This skill is used by people across a wide range of coding familiarity — from plumbers opening terminals for the first time to experienced developers. Pay attention to context cues:

- "evaluation" and "benchmark" are borderline, but OK
- For "JSON" and "assertion", look for clear signals the user knows those terms before using them unexplained

Briefly define terms if in doubt.

---

## Creating a skill

### Capture Intent

Start by understanding the user's intent. The current conversation might already contain a workflow the user wants to capture (e.g., they say "turn this into a skill"). If so, extract answers from the conversation history first — the tools used, the sequence of steps, corrections the user made, input/output formats observed. The user may need to fill the gaps, and should confirm before proceeding to the next step.

1. What should this skill enable Claude to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases to verify the skill works? Skills with objectively verifiable outputs (file transforms, data extraction, code generation, fixed workflow steps) benefit from test cases. Skills with subjective outputs (writing style, art) often don't need them. Suggest the appropriate default based on the skill type, but let the user decide.

### Interview and Research

Proactively ask questions about edge cases, input/output formats, example files, success criteria, and dependencies. Wait to write test prompts until you've got this part ironed out.

Check available MCPs - if useful for research (searching docs, finding similar skills, looking up best practices), research in parallel via subagents if available, otherwise inline. Come prepared with context to reduce burden on the user.

### Write the SKILL.md

Based on the user interview, fill in these components:

- **name**: Skill identifier (kebab-case)
- **description**: When to trigger, what it does. This is the primary triggering mechanism — include both what the skill does AND specific contexts for when to use it. All "when to use" info goes here, not in the body. Claude tends to undertrigger, so be a little "pushy": "Make sure to use this skill whenever the user mentions X or Y, even if they don't explicitly ask."
- **compatibility**: Required tools, dependencies (optional, rarely needed)
- **the rest of the skill :)**

See `references/writing-guide.md` for anatomy, progressive disclosure guidelines, writing patterns, and style notes.

#### Principle of Lack of Surprise

Skills must not contain malware, exploit code, or content that could compromise system security. Don't create misleading skills or skills designed to facilitate unauthorized access or data exfiltration.

### Test Cases

After writing the skill draft, come up with 2-3 realistic test prompts — the kind of thing a real user would actually say. Share them with the user: [you don't have to use this exact language] "Here are a few test cases I'd like to try. Do these look right, or do you want to add more?" Then run them.

Save test cases to `evals/evals.json`. Don't write assertions yet — just the prompts. You'll draft assertions in the next step while the runs are in progress.

```json
{
  "skill_name": "example-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "User's task prompt",
      "expected_output": "Description of expected result",
      "files": []
    }
  ]
}
```

See `references/schemas.md` for the full schema (including the `assertions` field, which you'll add later).

## Running and evaluating test cases

This section is one continuous sequence — don't stop partway through. Do NOT use `/skill-test` or any other testing skill.

Put results in `<skill-name>-workspace/` as a sibling to the skill directory. Within the workspace, organize results by iteration (`iteration-1/`, `iteration-2/`, etc.) and within that, each test case gets a directory (`eval-0/`, `eval-1/`, etc.). Don't create all of this upfront — just create directories as you go.

### Step 1: Spawn all runs (with-skill AND baseline) in the same turn

For each test case, spawn two subagents in the same turn — one with the skill, one without. This is important: don't spawn the with-skill runs first and then come back for baselines later. Launch everything at once so it all finishes around the same time.

**With-skill run:**

```
Execute this task:
- Skill path: <path-to-skill>
- Task: <eval prompt>
- Input files: <eval files if any, or "none">
- Save outputs to: <workspace>/iteration-<N>/eval-<ID>/with_skill/outputs/
- Outputs to save: <what the user cares about — e.g., "the .docx file", "the final CSV">
```

**Baseline run** (same prompt, but the baseline depends on context):

- **Creating a new skill**: no skill at all. Same prompt, no skill path, save to `without_skill/outputs/`.
- **Improving an existing skill**: the old version. Before editing, snapshot the skill (`cp -r <skill-path> <workspace>/skill-snapshot/`), then point the baseline subagent at the snapshot. Save to `old_skill/outputs/`.

Write an `eval_metadata.json` for each test case (assertions can be empty for now). Give each eval a descriptive name based on what it's testing — not just "eval-0". Use this name for the directory too. If this iteration uses new or modified eval prompts, create these files for each new eval directory — don't assume they carry over from previous iterations.

```json
{
  "eval_id": 0,
  "eval_name": "descriptive-name-here",
  "prompt": "The user's task prompt",
  "assertions": []
}
```

### Step 2: While runs are in progress, draft assertions

Don't just wait for the runs to finish — you can use this time productively. Draft quantitative assertions for each test case and explain them to the user. If assertions already exist in `evals/evals.json`, review them and explain what they check.

Good assertions are objectively verifiable and have descriptive names — they should read clearly in the benchmark viewer so someone glancing at the results immediately understands what each one checks. Subjective skills (writing style, design quality) are better evaluated qualitatively — don't force assertions onto things that need human judgment.

Update the `eval_metadata.json` files and `evals/evals.json` with the assertions once drafted. Also explain to the user what they'll see in the viewer — both the qualitative outputs and the quantitative benchmark.

### Step 3: As runs complete, capture timing data

When each subagent task completes, you receive a notification containing `total_tokens` and `duration_ms`. Save this data immediately to `timing.json` in the run directory:

```json
{
  "total_tokens": 84852,
  "duration_ms": 23332,
  "total_duration_seconds": 23.3
}
```

This is the only opportunity to capture this data — it comes through the task notification and isn't persisted elsewhere. Process each notification as it arrives rather than trying to batch them.

### Step 4: Grade, aggregate, and launch the viewer

Once all runs are done:

1. **Grade each run** — spawn a grader subagent (or grade inline) that reads `agents/grader.md` and evaluates each assertion against the outputs. Save results to `grading.json` in each run directory. The grading.json `assertion_results` array must use the fields `text`, `passed`, and `evidence` (not `name`/`met`/`details` or other variants) — the viewer depends on these exact field names. For assertions that can be checked programmatically, write and run a script rather than eyeballing it — scripts are faster, more reliable, and can be reused across iterations.

2. **Aggregate into benchmark** — run the aggregation script from the skill-creator directory:

   ```bash
   python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>
   ```

   This produces `benchmark.json` and `benchmark.md` with pass_rate, time, and tokens for each configuration, with mean ± stddev and the delta. If generating benchmark.json manually, see `references/schemas.md` for the exact schema the viewer expects.
   Put each with_skill version before its baseline counterpart.

3. **Do an analyst pass** — read the benchmark data and surface patterns the aggregate stats might hide. See `agents/analyzer.md` (the "Analyzing Benchmark Results" section) for what to look for — things like assertions that always pass regardless of skill (non-discriminating), high-variance evals (possibly flaky), and time/token tradeoffs.

4. **Launch the viewer** with both qualitative outputs and quantitative data:

   **POSIX (macOS / Linux):**
   ```bash
   nohup python <skill-creator-path>/eval-viewer/generate_review.py \
     <workspace>/iteration-N \
     --skill-name "my-skill" \
     --benchmark <workspace>/iteration-N/benchmark.json \
     > /dev/null 2>&1 &
   VIEWER_PID=$!
   ```

   **Windows (PowerShell):**
   ```powershell
   $viewerJob = Start-Job {
     python <skill-creator-path>/eval-viewer/generate_review.py `
       <workspace>/iteration-N `
       --skill-name "my-skill" `
       --benchmark <workspace>/iteration-N/benchmark.json
   }
   ```

   For iteration 2+, also pass `--previous-workspace <workspace>/iteration-<N-1>`.

   **Cowork / headless environments:** If `webbrowser.open()` is not available or the environment has no display, use `--static <output_path>` to write a standalone HTML file instead of starting a server. Feedback will be downloaded as a `feedback.json` file when the user clicks "Submit All Reviews". After download, copy `feedback.json` into the workspace directory for the next iteration to pick up.

Note: please use generate_review.py to create the viewer; there's no need to write custom HTML.

5. **Tell the user** something like: "I've opened the results in your browser. There are two tabs — 'Outputs' lets you click through each test case and leave feedback, 'Benchmark' shows the quantitative comparison. When you're done, come back here and let me know."

### What the user sees in the viewer

- **Outputs tab**: prompt, skill output (rendered inline), previous output (collapsed), assertion pass/fail (collapsed), feedback textbox (auto-saves), previous feedback.
- **Benchmark tab**: pass rates, timing, token usage per configuration, per-eval breakdowns and analyst observations.
- Navigation: prev/next buttons or arrow keys. "Submit All Reviews" saves all feedback to `feedback.json`.

### Step 5: Read the feedback

When the user tells you they're done, read `feedback.json`:

```json
{
  "reviews": [
    {
      "run_id": "eval-0-with_skill",
      "feedback": "the chart is missing axis labels",
      "timestamp": "..."
    },
    { "run_id": "eval-1-with_skill", "feedback": "", "timestamp": "..." },
    { "run_id": "eval-2-with_skill", "feedback": "perfect, love this", "timestamp": "..." }
  ],
  "status": "complete"
}
```

Empty feedback means the user thought it was fine. Focus your improvements on the test cases where the user had specific complaints.

Kill the viewer server when you're done with it:

**POSIX:**
```bash
kill $VIEWER_PID 2>/dev/null
```

**Windows (PowerShell):**
```powershell
Stop-Job $viewerJob; Remove-Job $viewerJob
```

---

## Improving the skill

This is the heart of the loop. You've run the test cases, the user has reviewed the results, and now you need to make the skill better based on their feedback.

### How to think about improvements

1. **Generalize, don't overfit.** You're creating a skill that needs to work for a million different prompts, not just the few you're testing. Resist fiddly example-specific tweaks — instead, understand why something failed and fix the underlying issue.

2. **Keep the prompt lean.** Read transcripts, not just final outputs. If the skill makes the model do unproductive things, remove the parts causing that behavior.

3. **Explain the why.** Today's LLMs are smart — give them context and reasoning rather than rigid ALWAYS/NEVER commands. If you find yourself writing heavy-handed constraints, reframe them as explanations.

4. **Bundle repeated work.** If multiple test runs independently wrote the same helper script, that script belongs in `scripts/`. Write it once, bundle it, and tell the skill to use it.

### The iteration loop

After improving the skill:

1. Apply your improvements to the skill
2. Rerun all test cases into a new `iteration-<N+1>/` directory, including baseline runs. If you're creating a new skill, the baseline is always `without_skill` (no skill) — that stays the same across iterations. If you're improving an existing skill, use your judgment on what makes sense as the baseline: the original version the user came in with, or the previous iteration.
3. Launch the reviewer with `--previous-workspace` pointing at the previous iteration
4. Wait for the user to review and tell you they're done
5. Read the new feedback, improve again, repeat

Keep going until:

- The user says they're happy
- The feedback is all empty (everything looks good)
- You're not making meaningful progress

---

## Advanced: Blind comparison

For a more rigorous comparison between two versions of a skill, there is a blind comparison system. Read `references/blind-comparison.md` for the full workflow. The basic idea: give two outputs to an independent agent without telling it which is which, and let it judge quality. Then analyze why the winner won.

This is optional and most users won't need it. The human review loop is usually sufficient.

---

## Description Optimization

The description field in SKILL.md frontmatter is the primary mechanism that determines whether Claude invokes a skill. After creating or improving a skill, offer to optimize the description for better triggering accuracy.

### Step 1: Generate trigger eval queries

Create 20 eval queries — a mix of should-trigger and should-not-trigger — saved as a flat JSON array:

```json
[
  { "query": "the user prompt", "should_trigger": true },
  { "query": "another prompt", "should_trigger": false }
]
```

Aim for 8–10 each way. Queries must be realistic and specific — not abstract like `"Format this data"` but concrete with file paths, company names, context. For should-not-trigger, use near-misses that share keywords but need something different, not obviously irrelevant ones.

See `references/description-optimization.md` for detailed query writing guidance and examples.

### Step 2: Review with user

Present the eval set to the user using the HTML template at `assets/eval_review.html`. Replace the placeholders (`__EVAL_DATA_PLACEHOLDER__`, `__SKILL_NAME_PLACEHOLDER__`, `__SKILL_DESCRIPTION_PLACEHOLDER__`), write to a temp file, and open it in a browser (see `references/environments.md` for POSIX vs Windows commands). The user edits queries and clicks "Export Eval Set" to download `eval_set.json`.

This step matters — bad eval queries lead to bad descriptions.

### Step 3: Run the optimization loop

Tell the user: "This will take some time — I'll run the optimization loop in the background and check on it periodically."

Save the eval set to the workspace, then run in the background:

```bash
python -m scripts.run_loop \
  --eval-set <path-to-trigger-eval.json> \
  --skill-path <path-to-skill> \
  --model <model-id-powering-this-session> \
  --max-iterations 5 \
  --verbose
```

Use the model ID from your system prompt (the one powering the current session) so the triggering test matches what the user actually experiences.

To use a non-default adapter (e.g., for testing in a different environment), add `--adapter kilo` or `--adapter manual`.

While it runs, periodically tail the output to give the user updates on which iteration it's on and what the scores look like.

This handles the full optimization loop automatically. It splits the eval set into 60% train and 40% held-out test, evaluates the current description (running each query 3 times to get a reliable trigger rate), then calls Claude to propose improvements based on what failed. It re-evaluates each new description on both train and test, iterating up to 5 times. When it's done, it opens an HTML report in the browser showing the results per iteration and returns JSON with `best_description` — selected by test score rather than train score to avoid overfitting.

### How skill triggering works

Skills appear in Claude's `available_skills` list with their name + description. Claude decides whether to consult a skill based on that description, and only invokes it for tasks it can't easily handle directly with basic tools. Complex, multi-step, or specialized queries reliably trigger skills when the description matches well. Keep eval queries substantive — simple queries like "read file X" won't trigger any skill regardless of description quality.

### Step 4: Apply the result

Take `best_description` from the JSON output and update the skill's SKILL.md frontmatter. Show the user before/after and report the scores.

---

### Package and Present (only if `present_files` tool is available)

Check whether you have access to the `present_files` tool. If you don't, skip this step. If you do, package the skill and present the .skill file to the user:

```bash
python -m scripts.package_skill <path/to/skill-folder>
```

After packaging, direct the user to the resulting `.skill` file path so they can install it.

---

## Reference files

The agents/ directory contains instructions for specialized subagents. Read them when you need to spawn the relevant subagent.

- `agents/grader.md` — How to evaluate assertions against outputs
- `agents/comparator.md` — How to do blind A/B comparison between two outputs
- `agents/analyzer.md` — How to analyze why one version beat another

The references/ directory has additional documentation:

- `references/schemas.md` — JSON structures for evals.json, grading.json, etc.
- `references/environments.md` — Platform-specific instructions (Claude.ai, Cowork, Windows)
- `references/blind-comparison.md` — Detailed blind comparison workflow
- `references/writing-guide.md` — SKILL.md anatomy, progressive disclosure, writing patterns
- `references/description-optimization.md` — Detailed trigger eval query generation guide
- `references/skill-guide-zh-TW.md` — 繁體中文導覽 (Traditional Chinese quick reference)

If you're in a non-default environment (Claude.ai, Cowork, Windows), read `references/environments.md` before starting.

---

Repeating one more time the core loop here for emphasis:

- Figure out what the skill is about
- Draft or edit the skill
- Run claude-with-access-to-the-skill on test prompts
- With the user, evaluate the outputs:
  - Create benchmark.json and run `eval-viewer/generate_review.py` to help the user review them
  - Run quantitative evals
- Repeat until you and the user are satisfied
- Package the final skill and return it to the user.

Please add steps to your TodoList, if you have such a thing, to make sure you don't forget. If you're in Cowork, please specifically put "Create evals JSON and run `eval-viewer/generate_review.py` so human can review test cases" in your TodoList to make sure it happens.

Good luck!
