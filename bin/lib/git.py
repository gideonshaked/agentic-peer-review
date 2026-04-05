"""Shared git helpers for peer review."""

import subprocess


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
