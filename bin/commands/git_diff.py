"""Capture git diff between a base ref and the current working tree."""

import json
import sys

from bin.lib.git import run_git


def main():
    if len(sys.argv) < 3:
        print("Usage: git-diff <working_dir> <base_ref>", file=sys.stderr)
        sys.exit(1)

    working_dir = sys.argv[1]
    base_ref = sys.argv[2]

    diff_out, _, rc = run_git("-C", working_dir, "diff", base_ref)
    if rc != 0:
        print(json.dumps({"error": True, "message": f"git diff failed with code {rc}"}))
        sys.exit(0)

    stats, _, _ = run_git("-C", working_dir, "diff", "--stat", base_ref)
    files_str, _, _ = run_git("-C", working_dir, "diff", "--name-only", base_ref)
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


if __name__ == "__main__":
    main()
