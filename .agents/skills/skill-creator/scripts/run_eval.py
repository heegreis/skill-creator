#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes the model to trigger (read the
skill) for a set of queries.  Outputs results as JSON on stdout.

Usage:
    python scripts/run_eval.py --eval-set evals/trigger_eval.json \\
        --skill-path .agents/skills/my-skill --verbose

    uv run scripts/run_eval.py --eval-set evals/trigger_eval.json \\
        --skill-path .agents/skills/my-skill --adapter claude-code

Examples:
    # Basic run with defaults (claude-code adapter, 3 runs per query)
    python scripts/run_eval.py --eval-set evals/eval_set.json --skill-path ./my-skill

    # Use a specific model, 5 parallel workers
    python scripts/run_eval.py --eval-set evals/eval_set.json --skill-path ./my-skill \\
        --model claude-opus-4-5 --num-workers 5

    # Dry-run (validates inputs, skips actual evaluation)
    python scripts/run_eval.py --eval-set evals/eval_set.json --skill-path ./my-skill \\
        --dry-run
"""

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scripts.trigger_adapters.claude_code import ClaudeCodeAdapter
from scripts.utils import parse_skill_md


def find_project_root() -> Path:
    """Find the project root by walking up from cwd looking for .claude/.

    Mimics how Claude Code discovers its project root, so the command file
    we create ends up where claude -p will look for it.
    """
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".claude").is_dir():
            return parent
    return current


def _make_adapter(adapter_name: str):
    """Return the appropriate TriggerAdapter instance."""
    if adapter_name == "claude-code":
        return ClaudeCodeAdapter()
    if adapter_name == "kilo":
        from scripts.trigger_adapters.kilo import KiloAdapter
        return KiloAdapter()
    if adapter_name == "manual":
        from scripts.trigger_adapters.manual import ManualAdapter
        return ManualAdapter()
    raise ValueError(
        f"Error: Unknown adapter '{adapter_name}' — "
        f"expected one of: claude-code, kilo, manual. "
        f"Try: python scripts/run_eval.py --adapter claude-code"
    )


def _run_single_query_worker(args_tuple: tuple) -> bool:
    """Top-level function for ProcessPoolExecutor (must be picklable)."""
    query, skill_name, skill_description, timeout, project_root, model, adapter_name = args_tuple
    adapter = _make_adapter(adapter_name)
    return adapter.check_triggered(
        query=query,
        skill_name=skill_name,
        skill_description=skill_description,
        timeout=timeout,
        project_root=project_root,
        model=model,
    )


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
    adapter_name: str = "claude-code",
) -> dict:
    """Run the full eval set and return results."""
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                worker_args = (
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                    adapter_name,
                )
                future = executor.submit(_run_single_query_worker, worker_args)
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append({
            "query": query,
            "should_trigger": should_trigger,
            "trigger_rate": trigger_rate,
            "triggers": sum(triggers),
            "runs": len(triggers),
            "pass": did_pass,
        })

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run trigger evaluation for a skill description",
        epilog=(
            "Examples:\n"
            "  python scripts/run_eval.py --eval-set evals/eval_set.json "
            "--skill-path ./my-skill\n"
            "  python scripts/run_eval.py --eval-set evals/eval_set.json "
            "--skill-path ./my-skill --adapter claude-code --verbose\n"
            "  python scripts/run_eval.py --eval-set evals/eval_set.json "
            "--skill-path ./my-skill --dry-run"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--description", default=None, help="Override description to test")
    parser.add_argument("--num-workers", type=int, default=10, help="Number of parallel workers (default: 10)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout per query in seconds (default: 30)")
    parser.add_argument("--runs-per-query", type=int, default=3, help="Number of runs per query (default: 3)")
    parser.add_argument("--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold (default: 0.5)")
    parser.add_argument(
        "--adapter",
        default="claude-code",
        choices=["claude-code", "kilo", "manual"],
        help="Trigger detection adapter to use (default: claude-code)",
    )
    parser.add_argument("--model", default=None, help="Model to use (default: user's configured model)")
    parser.add_argument("--verbose", action="store_true", help="Print progress to stderr")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs only, skip actual evaluation")
    args = parser.parse_args()

    eval_path = Path(args.eval_set)
    if not eval_path.exists():
        print(
            f"Error: Eval set file not found — expected a JSON file, got: {args.eval_set}. "
            f"Try: create the file first with queries like "
            f'[{{"query": "example", "should_trigger": true}}]',
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        eval_set = json.loads(eval_path.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {args.eval_set} — {e}", file=sys.stderr)
        sys.exit(1)

    skill_path = Path(args.skill_path)
    if not (skill_path / "SKILL.md").exists():
        print(
            f"Error: No SKILL.md found at {skill_path}. "
            f"Try: ensure the path points to a valid skill directory.",
            file=sys.stderr,
        )
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description
    project_root = find_project_root()

    if args.dry_run:
        print(json.dumps({
            "dry_run": True,
            "skill_name": name,
            "description": description,
            "eval_count": len(eval_set),
            "project_root": str(project_root),
            "adapter": args.adapter,
        }, indent=2))
        return

    if args.verbose:
        print(f"Evaluating: {description[:80]}...", file=sys.stderr)
        print(f"Adapter: {args.adapter}, workers: {args.num_workers}, timeout: {args.timeout}s", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
        adapter_name=args.adapter,
    )

    if args.verbose:
        summary = output["summary"]
        print(f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr)
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}", file=sys.stderr)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
