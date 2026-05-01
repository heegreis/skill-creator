#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""One-time migration tool to upgrade skill-creator workspaces to the new schema.

Changes applied:
  grading.json:   top-level "expectations" → "assertion_results"
  benchmark.json: runs[].expectations     → runs[].assertion_results
                  run_summary.delta values from strings to numbers
  history.json:   iterations[].expectation_pass_rate → assertion_pass_rate

A `.schema-migrated` marker file is written to each migrated workspace to
prevent re-running.

Usage:
    python scripts/migrate_schema.py <workspace_dir>
    python scripts/migrate_schema.py <workspace_dir> --dry-run

Examples:
    python scripts/migrate_schema.py my-skill-workspace/
    python scripts/migrate_schema.py my-skill-workspace/ --dry-run
    uv run scripts/migrate_schema.py my-skill-workspace/
"""

import argparse
import json
import sys
from pathlib import Path


MARKER_FILE = ".schema-migrated"


def migrate_grading_json(path: Path, dry_run: bool) -> bool:
    """Rename top-level 'expectations' → 'assertion_results' in grading.json."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Warning: Cannot read {path} — {e}", file=sys.stderr)
        return False

    if "expectations" not in data:
        return False  # already migrated or different schema

    data["assertion_results"] = data.pop("expectations")
    if not dry_run:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def migrate_benchmark_json(path: Path, dry_run: bool) -> bool:
    """Migrate benchmark.json:
      - runs[].expectations → runs[].assertion_results
      - run_summary.delta: string values → numeric values
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Warning: Cannot read {path} — {e}", file=sys.stderr)
        return False

    changed = False

    # Migrate runs[].expectations → assertion_results
    for run in data.get("runs", []):
        if "expectations" in run:
            run["assertion_results"] = run.pop("expectations")
            changed = True

    # Migrate delta strings → numbers
    delta = data.get("run_summary", {}).get("delta", {})
    for key in ("pass_rate", "time_seconds", "tokens"):
        val = delta.get(key)
        if isinstance(val, str):
            try:
                if key == "tokens":
                    delta[key] = int(float(val.replace("+", "")))
                else:
                    delta[key] = round(float(val.replace("+", "")), 4)
                changed = True
            except (ValueError, AttributeError):
                pass

    if not changed:
        return False

    if not dry_run:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def migrate_history_json(path: Path, dry_run: bool) -> bool:
    """Rename expectation_pass_rate → assertion_pass_rate in history.json."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"  Warning: Cannot read {path} — {e}", file=sys.stderr)
        return False

    changed = False
    for iteration in data.get("iterations", []):
        if "expectation_pass_rate" in iteration:
            iteration["assertion_pass_rate"] = iteration.pop("expectation_pass_rate")
            changed = True

    if not changed:
        return False

    if not dry_run:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def migrate_workspace(workspace: Path, dry_run: bool) -> dict:
    """Migrate all JSON files in a workspace directory tree."""
    stats = {"grading": 0, "benchmark": 0, "history": 0, "skipped": 0}

    marker = workspace / MARKER_FILE
    if marker.exists() and not dry_run:
        print(f"  Skipping {workspace} — already migrated (remove {MARKER_FILE} to re-run)")
        stats["skipped"] += 1
        return stats

    # grading.json files (anywhere in tree)
    for path in workspace.rglob("grading.json"):
        if migrate_grading_json(path, dry_run):
            action = "[dry-run] would update" if dry_run else "Updated"
            print(f"  {action}: {path}")
            stats["grading"] += 1

    # benchmark.json files
    for path in workspace.rglob("benchmark.json"):
        if migrate_benchmark_json(path, dry_run):
            action = "[dry-run] would update" if dry_run else "Updated"
            print(f"  {action}: {path}")
            stats["benchmark"] += 1

    # history.json files
    for path in workspace.rglob("history.json"):
        if migrate_history_json(path, dry_run):
            action = "[dry-run] would update" if dry_run else "Updated"
            print(f"  {action}: {path}")
            stats["history"] += 1

    if not dry_run and (stats["grading"] + stats["benchmark"] + stats["history"]) > 0:
        marker.write_text("Migrated by migrate_schema.py\n", encoding="utf-8")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Migrate skill-creator workspaces to the new assertion_results schema",
        epilog=(
            "Examples:\n"
            "  python scripts/migrate_schema.py my-skill-workspace/\n"
            "  python scripts/migrate_schema.py my-skill-workspace/ --dry-run\n"
            "  uv run scripts/migrate_schema.py my-skill-workspace/\n"
            "\nChanges applied:\n"
            "  grading.json:   expectations    → assertion_results\n"
            "  benchmark.json: runs[].expectations → runs[].assertion_results\n"
            "                  delta strings   → numeric values\n"
            "  history.json:   expectation_pass_rate → assertion_pass_rate"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "workspace",
        type=Path,
        help="Path to the workspace directory to migrate",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without writing files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if .schema-migrated marker exists",
    )
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    if not workspace.exists():
        print(
            f"Error: Workspace directory not found — got: {workspace}. "
            f"Try: check the path points to a valid workspace directory.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not workspace.is_dir():
        print(
            f"Error: Path is not a directory — got: {workspace}.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Remove marker if --force
    marker = workspace / MARKER_FILE
    if args.force and marker.exists():
        marker.unlink()
        print(f"Removed {marker} (--force)", file=sys.stderr)

    mode = "DRY RUN — " if args.dry_run else ""
    print(f"{mode}Migrating: {workspace}", file=sys.stderr)

    stats = migrate_workspace(workspace, args.dry_run)

    total = stats["grading"] + stats["benchmark"] + stats["history"]
    if total == 0 and stats["skipped"] == 0:
        print("No files needed migration.", file=sys.stderr)
    else:
        print(
            f"\n{mode}Summary: {stats['grading']} grading.json, "
            f"{stats['benchmark']} benchmark.json, "
            f"{stats['history']} history.json files updated.",
            file=sys.stderr,
        )

    # Structured JSON output to stdout
    print(json.dumps({
        "workspace": str(workspace),
        "dry_run": args.dry_run,
        "files_updated": stats,
        "total_updated": total,
    }, indent=2))


if __name__ == "__main__":
    main()
