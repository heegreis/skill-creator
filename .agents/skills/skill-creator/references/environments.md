# Platform-Specific Instructions

This file covers environment-specific adaptations for skill-creator.  The main
`SKILL.md` workflow is identical across platforms; only the mechanics listed
below differ.

---

## Claude Code (default)

The main SKILL.md workflow is written for Claude Code.  No special adaptations
needed.

**Description optimization**: `run_loop.py` and `run_eval.py` use `claude -p`
as a subprocess, which requires the `claude` CLI to be installed and
authenticated.

**Viewer**: `generate_review.py` opens `http://localhost:3117` automatically.
Kill the server with `kill $VIEWER_PID` (POSIX) or `Stop-Job $viewerJob`
(PowerShell) when done.

---

## Claude.ai

In Claude.ai there are no subagents and no `claude` CLI, so several mechanics
change:

- **Running test cases**: No subagents → no parallel execution.  For each test
  case, read the skill's SKILL.md, then follow its instructions to accomplish
  the test prompt yourself.  Do them one at a time.  Skip baseline runs — just
  use the skill to complete the task as requested.

- **Reviewing results**: If you cannot open a browser (Claude.ai VM has no
  display, or you're on a remote server), skip the browser viewer entirely.
  Instead, present results directly in the conversation: show the prompt and
  the output for each test case.  If the output is a file (e.g. `.docx`,
  `.xlsx`), save it to the filesystem and tell the user where it is so they
  can download and inspect it.  Ask for feedback inline.

- **Benchmarking**: Skip quantitative benchmarking — it relies on baseline
  comparisons which aren't meaningful without subagents.  Focus on qualitative
  user feedback.

- **The iteration loop**: Same as the main workflow — improve the skill, rerun
  the test cases, ask for feedback — just without the browser viewer.  You can
  still organise results into iteration directories on the filesystem if you
  have one.

- **Description optimization** (`run_loop.py` / `run_eval.py`): Requires
  `claude -p` — skip if you're on Claude.ai.

- **Blind comparison**: Requires subagents — skip it.

- **Packaging**: `package_skill.py` works anywhere with Python and a
  filesystem.  On Claude.ai, run it and the user can download the resulting
  `.skill` file.

- **Updating an existing skill**: The user might be asking you to update an
  existing skill, not create a new one.  In this case:
  - **Preserve the original name.** Note the skill's directory name and `name`
    frontmatter field — use them unchanged.
  - **Copy to a writeable location before editing.** The installed skill path
    may be read-only.  Copy to `/tmp/skill-name/`, edit there, and package from
    the copy.
  - **If packaging manually, stage in `/tmp/` first**, then copy to the output
    directory — direct writes may fail due to permissions.

---

## Cowork

In Cowork you have subagents but no browser or display:

- The main workflow (spawn test cases in parallel, run baselines, grade, etc.)
  all works.  If you run into severe timeout problems, it is OK to run the test
  prompts in series rather than parallel.

- **Viewer**: No display → use `--static <output_path>` to write a standalone
  HTML file.  Then share a link that the user can click to open the HTML in
  their own browser.

- **Feedback**: Since there is no running server, the viewer's "Submit All
  Reviews" button downloads `feedback.json` as a file.  You may have to
  request access to read it.

- **Description optimization**: `run_loop.py` / `run_eval.py` should work in
  Cowork fine since it uses `claude -p` via subprocess, not a browser.  Save
  this step until you've fully finished making the skill and the user agrees
  it's in good shape.

- **Packaging**: Works — `package_skill.py` just needs Python and a filesystem.

- **Updating an existing skill**: Follow the same update guidance as the
  Claude.ai section above.

- **Important**: After running tests, always generate the eval viewer BEFORE
  evaluating inputs yourself and attempting revisions.  You want to get the
  results in front of the human ASAP.

---

## Windows (PowerShell)

When running on Windows, substitute the POSIX shell commands shown in the main
workflow with their PowerShell equivalents:

| POSIX | PowerShell |
|-------|-----------|
| `nohup python … > /dev/null 2>&1 &` | `$viewerJob = Start-Job { python … }` |
| `VIEWER_PID=$!` | (captured in `$viewerJob`) |
| `kill $VIEWER_PID 2>/dev/null` | `Stop-Job $viewerJob; Remove-Job $viewerJob` |
| `/tmp/eval_review_<name>.html` | `$env:TEMP\eval_review_<name>.html` |
| `open /path/to/file.html` | `Start-Process /path/to/file.html` |

The `run_eval.py` Windows compatibility was achieved by replacing
`select.select` / `os.read(fd)` with `stdout.readline()` + `threading`, so the
script runs natively on Windows without any extra setup.
