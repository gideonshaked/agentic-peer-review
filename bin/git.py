#!/usr/bin/env python3
"""Shared git helpers for peer review."""

import json
import subprocess
import sys


def run_git(*args, cwd=None, timeout=30):
    """Run a git command and return (stdout, stderr, returncode)."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        timeout=timeout,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def cmd_git_diff():
    """Capture git diff between a base ref and the current working tree. CLI entrypoint."""
    if len(sys.argv) < 3:
        print("Usage: git-diff <working_dir> <base_ref>", file=sys.stderr)
        sys.exit(1)

    working_dir = sys.argv[1]
    base_ref = sys.argv[2]

    diff_out, _, rc = run_git("-C", working_dir, "diff", base_ref)
    if rc != 0:
        print(json.dumps({"error": True, "message": f"git diff failed with code {rc}"}))
        sys.exit(0)

    stats, _ = run_git("-C", working_dir, "diff", "--stat", base_ref)[:2]
    files_str, _ = run_git("-C", working_dir, "diff", "--name-only", base_ref)[:2]
    files_changed = [f for f in files_str.splitlines() if f]

    print(
        json.dumps(
            {
                "diff": diff_out,
                "files_changed": files_changed,
                "stats": stats if stats else "no changes",
            }
        )
    )


def main():
    cmd_git_diff()


if __name__ == "__main__":
    main()
