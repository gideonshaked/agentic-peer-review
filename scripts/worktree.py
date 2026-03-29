#!/usr/bin/env python3
"""Manage git worktrees for isolated peer review sessions.

Subcommands:
    setup                          Create a timestamped worktree + branch, sync uncommitted changes
    commit <path>                  Commit all changes in the worktree
    teardown <path> <branch>       Remove worktree and optionally delete branch
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone


def _run_git(*args, cwd=None, timeout=30):
    """Run a git command and return (stdout, returncode)."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        timeout=timeout,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def cmd_setup():
    """Create a worktree with a unique timestamped name, syncing uncommitted changes."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    branch_name = f"peer-review/{ts}"
    worktree_path = f"/tmp/peer-review-{ts}"

    # Create worktree from HEAD
    _, err, rc = _run_git("worktree", "add", worktree_path, "-b", branch_name)
    if rc != 0:
        print(json.dumps({"error": True, "message": f"Failed to create worktree: {err}"}))
        sys.exit(0)

    # Sync uncommitted changes: capture diff from original working tree, apply in worktree
    diff, _, rc = _run_git("diff", "HEAD")
    if rc == 0 and diff:
        apply = subprocess.run(
            ["git", "apply", "--allow-empty"],
            input=diff,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=worktree_path,
            timeout=30,
        )
        if apply.returncode != 0:
            # Non-fatal but warn: worktree proceeds without uncommitted changes
            import sys
            print(f"Warning: failed to sync uncommitted changes to worktree: {apply.stderr.strip()}", file=sys.stderr)

    # Also sync untracked files by checking for them
    untracked, _, _ = _run_git("ls-files", "--others", "--exclude-standard")
    if untracked:
        original_dir = os.getcwd()
        for rel_path in untracked.splitlines():
            src = os.path.join(original_dir, rel_path)
            dst = os.path.join(worktree_path, rel_path)
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)

    print(json.dumps({"worktree_path": worktree_path, "branch_name": branch_name}))


def cmd_commit(worktree_path):
    """Commit all changes in the worktree."""
    _run_git("-C", worktree_path, "add", "-A")
    _, err, rc = _run_git(
        "-C", worktree_path, "commit", "-m", "Peer review fixes",
    )
    if rc != 0:
        # No changes to commit is not an error
        if "nothing to commit" in err:
            print(json.dumps({"ok": True, "committed": False}))
            return
        print(json.dumps({"error": True, "message": f"Failed to commit: {err}"}))
        sys.exit(0)
    print(json.dumps({"ok": True, "committed": True}))


def cmd_teardown(worktree_path, branch_name, keep_branch=False):
    """Remove worktree and optionally delete the branch."""
    _run_git("worktree", "remove", worktree_path, "--force")
    if not keep_branch:
        _run_git("branch", "-D", branch_name)
    print(json.dumps({"ok": True}))


def main():
    if len(sys.argv) < 2:
        print("Usage: worktree <setup|commit|teardown> [args]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "setup":
        cmd_setup()
    elif cmd == "commit":
        if len(sys.argv) < 3:
            print("Usage: worktree commit <worktree_path>", file=sys.stderr)
            sys.exit(1)
        cmd_commit(sys.argv[2])
    elif cmd == "teardown":
        if len(sys.argv) < 4:
            print("Usage: worktree teardown <path> <branch> [--keep-branch]", file=sys.stderr)
            sys.exit(1)
        keep = "--keep-branch" in sys.argv
        cmd_teardown(sys.argv[2], sys.argv[3], keep_branch=keep)
    else:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
