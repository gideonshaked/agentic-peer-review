#!/usr/bin/env python3
"""Manage the structured JSON change log for peer review sessions.

The log file path is derived automatically from the working directory
via session_log_path() — no need to pass it as an argument.

Subcommands:
    init                           Create a new change log
    start-round --round-num N      Start a new round
    add-finding --id --file ...    Add a finding to the current round
    add-fix --finding-id ...       Add a fix to the current round
    add-skip --finding-id ...      Add a skipped finding to the current round
    end-round                      Close the current round
    finalize                       Compute summary, set completed_at, print JSON
    render-md --output <path>      Render the finalized JSON as a markdown log file
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

from bin.session import session_log_path


def _load_log():
    """Load the session log."""
    path = session_log_path()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_log(data):
    """Save the session log."""
    path = session_log_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def cmd_init():
    """Create a new change log from CLI arguments. Also captures base commit."""
    parser = argparse.ArgumentParser(description="Initialize change log")
    parser.add_argument("--agent", default="")
    parser.add_argument("--max-rounds", type=int, default=0)
    parser.add_argument("--focus", default="")
    parser.add_argument("--instructions", default="")
    parser.add_argument("--worktree", action="store_true", default=False)
    parser.add_argument("--language", default="")
    parser.add_argument("--framework", default="")
    parser.add_argument("--working-dir", default="")
    args = parser.parse_args()

    path = session_log_path()

    # Capture base commit SHA
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
        )
        base_commit = result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        base_commit = ""

    data = {
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
                "language": args.language,
                "framework": args.framework,
                "working_dir": args.working_dir,
            },
        },
        "rounds": [],
    }
    _save_log(data)
    print(json.dumps({"log_file": path, "base_commit": base_commit}))


def cmd_start_round():
    """Start a new round in the change log."""
    parser = argparse.ArgumentParser(description="Start a new round")
    parser.add_argument("--round-num", type=int, required=True)
    args = parser.parse_args()

    data = _load_log()
    data["rounds"].append(
        {
            "round_num": args.round_num,
            "findings": [],
            "fixes": [],
            "skipped": [],
        }
    )
    _save_log(data)
    print(json.dumps({"ok": True}))


def cmd_add_finding():
    """Add a finding to the current round."""
    parser = argparse.ArgumentParser(description="Add a finding")
    parser.add_argument("--id", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--line", default="")
    parser.add_argument("--severity", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--description", required=True)
    args = parser.parse_args()

    data = _load_log()
    if not data["rounds"]:
        print(
            json.dumps(
                {"error": True, "message": "No active round. Call start-round first."}
            )
        )
        sys.exit(0)
    data["rounds"][-1]["findings"].append(
        {
            "id": args.id,
            "file": args.file,
            "line": args.line,
            "severity": args.severity,
            "category": args.category,
            "description": args.description,
        }
    )
    _save_log(data)
    print(json.dumps({"ok": True}))


def cmd_add_fix():
    """Add a fix to the current round."""
    parser = argparse.ArgumentParser(description="Add a fix")
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--what-changed", required=True)
    parser.add_argument("--why", required=True)
    args = parser.parse_args()

    data = _load_log()
    if not data["rounds"]:
        print(
            json.dumps(
                {"error": True, "message": "No active round. Call start-round first."}
            )
        )
        sys.exit(0)
    data["rounds"][-1]["fixes"].append(
        {
            "finding_id": args.finding_id,
            "file": args.file,
            "what_changed": args.what_changed,
            "why": args.why,
        }
    )
    _save_log(data)
    print(json.dumps({"ok": True}))


def cmd_add_skip():
    """Add a skipped finding to the current round."""
    parser = argparse.ArgumentParser(description="Add a skipped finding")
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--severity", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()

    data = _load_log()
    if not data["rounds"]:
        print(
            json.dumps(
                {"error": True, "message": "No active round. Call start-round first."}
            )
        )
        sys.exit(0)
    data["rounds"][-1]["skipped"].append(
        {
            "finding_id": args.finding_id,
            "file": args.file,
            "severity": args.severity,
            "reason": args.reason,
        }
    )
    _save_log(data)
    print(json.dumps({"ok": True}))


def cmd_end_round():
    """Close the current round."""
    data = _load_log()
    if not data["rounds"]:
        print(json.dumps({"error": True, "message": "No active round."}))
        sys.exit(0)
    print(json.dumps({"ok": True, "round_num": data["rounds"][-1]["round_num"]}))


def cmd_finalize():
    """Compute summary, set completed_at, print finalized JSON."""
    data = _load_log()
    data["meta"]["completed_at"] = datetime.now(timezone.utc).isoformat()
    data["summary"] = {
        "rounds_completed": len(data["rounds"]),
        "total_findings": sum(len(r.get("findings", [])) for r in data["rounds"]),
        "total_fixes": sum(len(r.get("fixes", [])) for r in data["rounds"]),
        "total_skipped": sum(len(r.get("skipped", [])) for r in data["rounds"]),
    }
    _save_log(data)
    print(json.dumps(data))


def cmd_render_md(output_path):
    """Render the finalized JSON as a markdown file."""
    data = _load_log()

    meta = data["meta"]
    lines = [
        "# Peer Review Log",
        "",
        f"- **Agent:** {meta['agent']}",
        f"- **Project:** {meta['project'].get('language', 'unknown')}"
        + (
            f"/{meta['project']['framework']}"
            if meta["project"].get("framework")
            else ""
        ),
        f"- **Working directory:** {meta['project'].get('working_dir', '')}",
        f"- **Started:** {meta.get('started_at', '')}",
        f"- **Completed:** {meta.get('completed_at', '')}",
    ]
    if meta.get("focus"):
        lines.append(f"- **Focus:** {meta['focus']}")
    if meta.get("message"):
        lines.append(f"- **Message:** {meta['message']}")
    lines.append("")

    for rnd in data.get("rounds", []):
        lines.append(f"## Round {rnd['round_num']}")
        lines.append("")

        findings = rnd.get("findings", [])
        if findings:
            lines.append(f"### Findings ({len(findings)})")
            lines.append("")
            for f in findings:
                lines.append(
                    f"- **[{f.get('id', '')}]** `{f.get('file', '')}:{f.get('line', '')}`"
                    f" ({f.get('severity', '')}/{f.get('category', '')})"
                    f" — {f.get('description', '')}"
                )
            lines.append("")

        fixes = rnd.get("fixes", [])
        if fixes:
            lines.append(f"### Fixes ({len(fixes)})")
            lines.append("")
            for fix in fixes:
                lines.append(
                    f"- **{fix.get('finding_id', '')}** `{fix.get('file', '')}`"
                    f" — {fix.get('what_changed', '')} ({fix.get('why', '')})"
                )
            lines.append("")

        skipped = rnd.get("skipped", [])
        if skipped:
            lines.append(f"### Skipped ({len(skipped)})")
            lines.append("")
            for s in skipped:
                lines.append(
                    f"- **{s.get('finding_id', '')}** `{s.get('file', '')}`"
                    f" ({s.get('severity', '')})"
                    f" — {s.get('reason', '')}"
                )
            lines.append("")

    summary = data.get("summary", {})
    if summary:
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- Rounds completed: {summary.get('rounds_completed', 0)}")
        lines.append(f"- Total findings: {summary.get('total_findings', 0)}")
        lines.append(f"- Total fixes: {summary.get('total_fixes', 0)}")
        lines.append(f"- Total skipped: {summary.get('total_skipped', 0)}")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(json.dumps({"ok": True, "output": output_path}))


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: change_log <init|start-round|add-finding|add-fix|add-skip|end-round|finalize|render-md> [args]",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = sys.argv[1]
    # Shift argv so argparse in subcommands sees the right args
    sys.argv = [f"change-log {cmd}"] + sys.argv[2:]

    if cmd == "init":
        cmd_init()
    elif cmd == "start-round":
        cmd_start_round()
    elif cmd == "add-finding":
        cmd_add_finding()
    elif cmd == "add-fix":
        cmd_add_fix()
    elif cmd == "add-skip":
        cmd_add_skip()
    elif cmd == "end-round":
        cmd_end_round()
    elif cmd == "finalize":
        cmd_finalize()
    elif cmd == "render-md":
        output_path = ""
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_path = sys.argv[i + 1]
        if not output_path:
            print("--output <path> is required", file=sys.stderr)
            sys.exit(1)
        cmd_render_md(output_path)
    else:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
