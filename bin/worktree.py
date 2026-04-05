#!/usr/bin/env python3
"""Manage git worktrees for isolated peer review sessions.

Subcommands:
    setup                          Create worktree, sync changes, commit baseline
    commit <path> [--message M]    Commit fixes in the worktree (per-round)
    merge <path> <baseline_sha>    Apply per-round commits to the original working directory
    teardown <path> <branch>       Remove worktree and optionally delete branch
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone


def _run_git(*args, cwd=None, timeout=30):
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


def cmd_setup():
    """Create worktree, sync uncommitted + untracked files, commit as baseline."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    branch_name = f"peer-review/{ts}"
    worktree_path = tempfile.mkdtemp(prefix=f"peer-review-{ts}-")
    os.rmdir(worktree_path)  # git worktree add needs a non-existing path

    # Create worktree from HEAD
    _, err, rc = _run_git("worktree", "add", worktree_path, "-b", branch_name)
    if rc != 0:
        print(
            json.dumps({"error": True, "message": f"Failed to create worktree: {err}"})
        )
        sys.exit(0)

    # Sync working state using git stash.
    # stash create makes a stash commit without touching the working tree.
    # --include-untracked captures untracked files too.
    stash_sha, _, rc = _run_git("stash", "create", "--include-untracked")
    if rc == 0 and stash_sha:
        # Apply the stash in the worktree
        _, err, rc = _run_git("-C", worktree_path, "stash", "apply", stash_sha)
        if rc != 0:
            print(
                f"Warning: failed to sync working state to worktree: {err}",
                file=sys.stderr,
            )

    # Commit everything as baseline (so we can later diff baseline..fixes)
    _run_git("-C", worktree_path, "add", "-A")
    _run_git("-C", worktree_path, "commit", "-m", "Baseline: synced working state")

    # Capture baseline SHA
    baseline_sha, _, _ = _run_git("-C", worktree_path, "rev-parse", "HEAD")

    print(
        json.dumps(
            {
                "worktree_path": worktree_path,
                "branch_name": branch_name,
                "baseline_sha": baseline_sha,
            }
        )
    )


def cmd_commit(worktree_path, message="Peer review fixes"):
    """Commit review fixes in the worktree. Returns commit SHA on success."""
    _, add_err, add_rc = _run_git("-C", worktree_path, "add", "-A")
    if add_rc != 0:
        print(
            json.dumps(
                {"error": True, "message": f"Failed to stage changes: {add_err}"}
            )
        )
        sys.exit(0)
    stdout, err, rc = _run_git("-C", worktree_path, "commit", "-m", message)
    if rc != 0:
        # "nothing to commit" appears in stdout, not stderr
        if "nothing to commit" in stdout or "nothing to commit" in err:
            print(json.dumps({"ok": True, "committed": False}))
            return
        print(
            json.dumps({"error": True, "message": f"Failed to commit: {err or stdout}"})
        )
        sys.exit(0)
    sha, _, _ = _run_git("-C", worktree_path, "rev-parse", "HEAD")
    print(json.dumps({"ok": True, "committed": True, "sha": sha}))


def cmd_merge(worktree_path, baseline_sha):
    """Apply per-round commits from the worktree to the original working directory.

    Uses git format-patch + git am --3way to preserve individual round commits.
    Stashes uncommitted changes before applying and restores them after.
    """

    # Check if there are any round commits to apply
    count_str, _, rc = _run_git(
        "-C", worktree_path, "rev-list", "--count", f"{baseline_sha}..HEAD"
    )
    if rc != 0 or count_str == "0":
        print(
            json.dumps(
                {"ok": True, "applied": False, "message": "No round commits to apply"}
            )
        )
        return

    # Record pre-merge HEAD for rollback
    pre_merge_head, _, _ = _run_git("rev-parse", "HEAD")

    # Check if working directory is dirty and needs stashing
    status_out, _, _ = _run_git("status", "--porcelain")
    stashed = False
    if status_out:
        _, stash_err, stash_rc = _run_git(
            "stash", "push", "--include-untracked", "-m", "peer-review: pre-merge stash"
        )
        if stash_rc != 0:
            print(
                json.dumps(
                    {
                        "error": True,
                        "message": f"Failed to stash uncommitted changes: {stash_err}",
                    }
                )
            )
            sys.exit(0)
        stashed = True

    # Generate patches — one per round commit
    # Do NOT use _run_git here — it strips whitespace which corrupts patches
    result = subprocess.run(
        [
            "git",
            "-C",
            worktree_path,
            "format-patch",
            "--stdout",
            f"{baseline_sha}..HEAD",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if result.returncode != 0 or not result.stdout.strip():
        if stashed:
            _run_git("stash", "pop", "--index")
        print(
            json.dumps(
                {
                    "error": True,
                    "message": f"Failed to generate patches: {result.stderr.strip()}",
                }
            )
        )
        sys.exit(0)

    # Write patches to temp file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".patch", delete=False, encoding="utf-8"
    ) as f:
        f.write(result.stdout)
        patch_path = f.name

    try:
        # Apply patches as individual commits
        am = subprocess.run(
            ["git", "am", "--3way", patch_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        if am.returncode != 0:
            # Rollback: abort the am and reset to pre-merge state
            _run_git("am", "--abort")
            _run_git("reset", "--soft", pre_merge_head)
            if stashed:
                _run_git("stash", "pop", "--index")
            print(
                json.dumps(
                    {
                        "error": True,
                        "message": f"Failed to apply round commits: {am.stderr.strip()}",
                        "pre_merge_head": pre_merge_head,
                    }
                )
            )
            sys.exit(0)
    finally:
        os.unlink(patch_path)

    # Count how many commits were applied
    applied_str, _, _ = _run_git("rev-list", "--count", f"{pre_merge_head}..HEAD")
    commits_applied = int(applied_str) if applied_str.isdigit() else 0

    # Restore stashed changes
    stash_warning = ""
    if stashed:
        _, pop_err, pop_rc = _run_git("stash", "pop", "--index")
        if pop_rc != 0:
            stash_warning = (
                f"Commits applied but stash pop failed: {pop_err}. "
                "Run 'git stash pop' manually to restore your uncommitted changes."
            )

    out = {"ok": True, "applied": True, "commits_applied": commits_applied}
    if stash_warning:
        out["stash_warning"] = stash_warning
    print(json.dumps(out))


def cmd_teardown(worktree_path, branch_name, keep_branch=False):
    """Remove worktree and optionally delete the branch."""
    _run_git("worktree", "remove", worktree_path, "--force")
    if not keep_branch:
        _run_git("branch", "-D", branch_name)
    print(json.dumps({"ok": True}))


def main():
    if len(sys.argv) < 2:
        print("Usage: worktree <setup|commit|merge|teardown> [args]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "setup":
        cmd_setup()
    elif cmd == "commit":
        if len(sys.argv) < 3:
            print(
                "Usage: worktree commit <worktree_path> [--message MSG]",
                file=sys.stderr,
            )
            sys.exit(1)
        message = "Peer review fixes"
        if "--message" in sys.argv:
            idx = sys.argv.index("--message")
            if idx + 1 < len(sys.argv):
                message = sys.argv[idx + 1]
        cmd_commit(sys.argv[2], message=message)
    elif cmd == "merge":
        if len(sys.argv) < 4:
            print(
                "Usage: worktree merge <worktree_path> <baseline_sha>", file=sys.stderr
            )
            sys.exit(1)
        cmd_merge(sys.argv[2], sys.argv[3])
    elif cmd == "teardown":
        if len(sys.argv) < 4:
            print(
                "Usage: worktree teardown <path> <branch> [--keep-branch]",
                file=sys.stderr,
            )
            sys.exit(1)
        keep = "--keep-branch" in sys.argv
        cmd_teardown(sys.argv[2], sys.argv[3], keep_branch=keep)
    else:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
