"""Initialize a peer review session.

Combines argument parsing, project detection, change log creation,
and optional worktree setup into a single command.

Prints the settings box, then a JSON object on the last line with
all values Claude needs for the session.
"""

import argparse
import glob
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version

from bin.commands.change_log import _save_log
from bin.commands.worktree import cmd_setup
from bin.lib.checks import get_available_checks
from bin.lib.formatting import render_settings_box
from bin.lib.git import run_git

# Map project files to (language, framework) pairs. First match wins.
PROJECT_SIGNATURES = [
    ("package.json", "TypeScript", ""),
    ("Cargo.toml", "Rust", ""),
    ("go.mod", "Go", ""),
    ("pyproject.toml", "Python", ""),
    ("requirements.txt", "Python", ""),
    ("Gemfile", "Ruby", ""),
    ("pom.xml", "Java", ""),
    ("build.gradle", "Java", ""),
    ("*.csproj", "C#", ""),
    ("mix.exs", "Elixir", ""),
    ("composer.json", "PHP", ""),
]

FRAMEWORK_HINTS = {
    "Python": {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "streamlit": "Streamlit",
    },
    "TypeScript": {
        "react": "React",
        "next": "Next.js",
        "vue": "Vue",
        "angular": "Angular",
        "express": "Express",
    },
    "JavaScript": {
        "react": "React",
        "next": "Next.js",
        "vue": "Vue",
        "angular": "Angular",
        "express": "Express",
    },
    "Ruby": {
        "rails": "Rails",
        "sinatra": "Sinatra",
    },
}


def _detect_language(working_dir):
    """Detect language and framework from project files."""
    language = ""
    framework = ""

    for pattern, lang, fw in PROJECT_SIGNATURES:
        if glob.glob(os.path.join(working_dir, pattern)):
            language = lang
            framework = fw
            break

    if not language:
        return language, framework

    if language == "TypeScript" and not os.path.exists(
        os.path.join(working_dir, "tsconfig.json")
    ):
        language = "JavaScript"

    hints = FRAMEWORK_HINTS.get(language, {})
    if hints:
        dep_content = ""
        if language == "Python":
            for f in ("pyproject.toml", "requirements.txt"):
                path = os.path.join(working_dir, f)
                if os.path.exists(path):
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        dep_content = fh.read().lower()
                    break
        elif language in ("TypeScript", "JavaScript"):
            path = os.path.join(working_dir, "package.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8", errors="replace") as fh:
                    dep_content = fh.read().lower()
        elif language == "Ruby":
            path = os.path.join(working_dir, "Gemfile")
            if os.path.exists(path):
                with open(path, encoding="utf-8", errors="replace") as fh:
                    dep_content = fh.read().lower()

        for key, fw_name in hints.items():
            if key in dep_content:
                framework = fw_name
                break

    return language, framework


def main():
    parser = argparse.ArgumentParser(
        prog="peer-review",
        description="Iterative AI peer review that finds and fixes issues in your codebase",
        exit_on_error=False,
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=version("agentic-peer-review"),
    )
    parser.add_argument(
        "--agent",
        choices=["claude", "codex", "gemini"],
        default="claude",
        help="AI agent to use for review (default: claude)",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=5,
        help="Maximum review-fix cycles (default: 5). Stops early if no issues found.",
    )
    parser.add_argument(
        "--focus",
        default="",
        help="Narrow review scope to a specific file or directory path",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds for each review agent invocation (default: 300)",
    )
    parser.add_argument(
        "--worktree",
        action="store_true",
        default=False,
        help=(
            "Run fixes in a git worktree. Each round is committed separately "
            "and ported as individual commits on merge. Shows diff at end and "
            "asks to merge or discard"
        ),
    )
    parser.add_argument(
        "--log",
        default="",
        help="Write findings and fix/skip decisions to the specified file",
    )
    all_checks = get_available_checks()
    parser.add_argument(
        "--only",
        default="",
        help=f"Comma-separated list of checks to run (default: all). Available: {', '.join(all_checks)}",
    )
    parser.add_argument(
        "--skip",
        default="",
        help=f"Comma-separated list of checks to exclude. Available: {', '.join(all_checks)}",
    )
    parser.add_argument(
        "instructions",
        nargs="?",
        default="",
        help="Optional review instructions",
    )

    try:
        args = parser.parse_args()
    except argparse.ArgumentError as e:
        print(json.dumps({"error": True, "message": f"Invalid arguments: {e}"}))
        sys.exit(0)

    if args.timeout < 1:
        print(
            json.dumps(
                {"error": True, "message": "--timeout must be a positive integer"}
            )
        )
        sys.exit(0)

    if args.max_rounds < 1:
        print(json.dumps({"error": True, "message": "--max-rounds must be at least 1"}))
        sys.exit(0)

    if args.agent != "claude":
        install_hints = {
            "codex": "Install Codex CLI: npm install -g @openai/codex",
            "gemini": "Install Gemini CLI: see https://github.com/google-gemini/gemini-cli",
        }
        if shutil.which(args.agent) is None:
            print(
                json.dumps(
                    {
                        "error": True,
                        "message": f"{args.agent} CLI not found. {install_hints.get(args.agent, '')}",
                    }
                )
            )
            sys.exit(0)

    if args.only and args.skip:
        print(
            json.dumps(
                {"error": True, "message": "--only and --skip cannot be used together"}
            )
        )
        sys.exit(0)

    if args.only:
        requested = [c.strip() for c in args.only.split(",")]
        invalid = [c for c in requested if c not in all_checks]
        if invalid:
            print(
                json.dumps(
                    {
                        "error": True,
                        "message": f"Unknown check(s): {', '.join(invalid)}. Available: {', '.join(all_checks)}",
                    }
                )
            )
            sys.exit(0)
        active_checks = requested
    elif args.skip:
        excluded = [c.strip() for c in args.skip.split(",")]
        invalid = [c for c in excluded if c not in all_checks]
        if invalid:
            print(
                json.dumps(
                    {
                        "error": True,
                        "message": f"Unknown check(s): {', '.join(invalid)}. Available: {', '.join(all_checks)}",
                    }
                )
            )
            sys.exit(0)
        active_checks = [c for c in all_checks if c not in excluded]
    else:
        active_checks = all_checks

    # Detect project
    working_dir = os.getcwd()
    language, framework = _detect_language(working_dir)
    language = language or "unknown"

    # Print settings box
    settings = {
        "error": False,
        "agent": args.agent,
        "max_rounds": args.max_rounds,
        "instructions": args.instructions,
        "focus": args.focus,
        "timeout": args.timeout,
        "worktree": args.worktree,
        "log": args.log,
        "checks": active_checks,
        "all_checks": all_checks,
    }
    render_settings_box(json.dumps(settings))

    # Create session change log
    try:
        stdout, _, rc = run_git("rev-parse", "HEAD", timeout=10)
        base_commit = stdout if rc == 0 else ""
    except Exception:
        base_commit = ""

    log_data = {
        "meta": {
            "agent": args.agent,
            "max_rounds": args.max_rounds,
            "focus": args.focus,
            "instructions": args.instructions,
            "worktree": args.worktree,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": "",
            "base_commit": base_commit,
            "project": {
                "language": language,
                "framework": framework,
                "working_dir": working_dir,
            },
        },
        "rounds": [],
    }
    _save_log(log_data)

    # Set up worktree if requested
    worktree_path = ""
    branch_name = ""
    baseline_sha = ""
    if args.worktree:
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            cmd_setup()
        wt_result = json.loads(f.getvalue())
        if wt_result.get("error"):
            print(json.dumps(wt_result))
            sys.exit(0)
        worktree_path = wt_result["worktree_path"]
        branch_name = wt_result["branch_name"]
        baseline_sha = wt_result["baseline_sha"]

    result = {
        "error": False,
        "agent": args.agent,
        "max_rounds": args.max_rounds,
        "instructions": args.instructions,
        "focus": args.focus,
        "timeout": args.timeout,
        "worktree": args.worktree,
        "log": args.log,
        "checks": active_checks,
        "language": language,
        "framework": framework,
        "working_dir": worktree_path if args.worktree else working_dir,
        "original_working_dir": working_dir,
        "base_commit": base_commit,
        "worktree_path": worktree_path,
        "branch_name": branch_name,
        "baseline_sha": baseline_sha,
        "start_time": int(time.time()),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
