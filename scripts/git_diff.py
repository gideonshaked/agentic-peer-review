#!/usr/bin/env python3
"""Capture git diff between a base ref and the current working tree.

Returns JSON with the full diff text, list of changed files, and stats summary.
"""

import json
import subprocess
import sys


def run_git(working_dir, *args):
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", "-C", working_dir, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    return result.stdout.strip(), result.returncode


def main():
    if len(sys.argv) < 3:
        print("Usage: git_diff <working_dir> <base_ref>", file=sys.stderr)
        sys.exit(1)

    working_dir = sys.argv[1]
    base_ref = sys.argv[2]

    diff_text, rc = run_git(working_dir, "diff", base_ref)
    if rc != 0:
        print(json.dumps({"error": True, "message": f"git diff failed with code {rc}"}))
        sys.exit(0)

    stats, _ = run_git(working_dir, "diff", "--stat", base_ref)
    files_str, _ = run_git(working_dir, "diff", "--name-only", base_ref)
    files_changed = [f for f in files_str.splitlines() if f]

    result = {
        "diff": diff_text,
        "files_changed": files_changed,
        "stats": stats if stats else "no changes",
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
