#!/usr/bin/env python3
"""Manage git worktrees for isolated peer review sessions.

Subcommands:
    setup                          Create worktree, sync changes, commit baseline
    commit <path>                  Commit fixes in the worktree
    merge <path> <baseline_sha>    Apply only the fix diff to the original working directory
    teardown <path> <branch>       Remove worktree and optionally delete branch
"""

import json
import os
import shutil
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

    # Sync uncommitted tracked changes
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
            print(
                f"Warning: failed to sync uncommitted changes: {apply.stderr.strip()}",
                file=sys.stderr,
            )

    # Sync untracked files
    untracked, _, _ = _run_git("ls-files", "--others", "--exclude-standard")
    if untracked:
        original_dir = os.getcwd()
        for rel_path in untracked.splitlines():
            src = os.path.join(original_dir, rel_path)
            dst = os.path.realpath(os.path.join(worktree_path, rel_path))
            if not dst.startswith(os.path.realpath(worktree_path)):
                continue  # skip paths that escape the worktree
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)

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


def cmd_commit(worktree_path):
    """Commit review fixes in the worktree."""
    _, add_err, add_rc = _run_git("-C", worktree_path, "add", "-A")
    if add_rc != 0:
        print(
            json.dumps(
                {"error": True, "message": f"Failed to stage changes: {add_err}"}
            )
        )
        sys.exit(0)
    stdout, err, rc = _run_git("-C", worktree_path, "commit", "-m", "Peer review fixes")
    if rc != 0:
        # "nothing to commit" appears in stdout, not stderr
        if "nothing to commit" in stdout or "nothing to commit" in err:
            print(json.dumps({"ok": True, "committed": False}))
            return
        print(
            json.dumps({"error": True, "message": f"Failed to commit: {err or stdout}"})
        )
        sys.exit(0)
    print(json.dumps({"ok": True, "committed": True}))


def cmd_merge(worktree_path, baseline_sha):
    """Apply only the fix changes (baseline..HEAD) to the original working directory.

    Uses git diff + git apply instead of git merge to avoid conflicts
    with untracked files in the original working directory.
    """
    import tempfile

    # Get the diff between baseline and current HEAD (only the fixes)
    # Do NOT use _run_git here — it strips whitespace which corrupts patches
    result = subprocess.run(
        ["git", "-C", worktree_path, "diff", f"{baseline_sha}..HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    diff = result.stdout
    rc = result.returncode
    if rc != 0 or not diff.strip():
        print(
            json.dumps(
                {"ok": True, "applied": False, "message": "No fix changes to apply"}
            )
        )
        return

    # Write patch to temp file to avoid stdin encoding issues
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".patch", delete=False, encoding="utf-8"
    ) as f:
        f.write(diff)
        patch_path = f.name

    try:
        apply = subprocess.run(
            ["git", "apply", patch_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
        if apply.returncode != 0:
            print(
                json.dumps(
                    {
                        "error": True,
                        "message": f"Failed to apply fixes: {apply.stderr.strip()}",
                    }
                )
            )
            sys.exit(0)
        print(json.dumps({"ok": True, "applied": True}))
    finally:
        os.unlink(patch_path)


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
            print("Usage: worktree commit <worktree_path>", file=sys.stderr)
            sys.exit(1)
        cmd_commit(sys.argv[2])
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
