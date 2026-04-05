"""Manage the structured JSON change log for peer review sessions.

Subcommands:
    init                           Create a new change log
    add-finding --round-num N ...  Add a finding (auto-creates round)
    add-fix --round-num N ...      Add a fix (auto-creates round)
    add-skip --round-num N ...     Add a skipped finding (auto-creates round)
    finalize [--log <path>]        Compute summary, print summary box, optional markdown
    render-md --output <path>      Render the finalized JSON as a markdown log file
"""

import argparse
import json
import sys
from datetime import datetime, timezone

from bin.lib.formatting import box
from bin.lib.git import run_git
from bin.lib.session import session_log_path


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

    try:
        stdout, _, rc = run_git("rev-parse", "HEAD", timeout=10)
        base_commit = stdout if rc == 0 else ""
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


def _ensure_round(data, round_num):
    """Ensure a round exists for the given round_num, creating it if needed."""
    for rnd in data["rounds"]:
        if rnd["round_num"] == round_num:
            return rnd
    rnd = {"round_num": round_num, "findings": [], "fixes": [], "skipped": []}
    data["rounds"].append(rnd)
    return rnd


def cmd_add_finding():
    """Add a finding to a round (auto-creates the round if needed)."""
    parser = argparse.ArgumentParser(description="Add a finding")
    parser.add_argument("--round-num", type=int, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--line", default="")
    parser.add_argument("--severity", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--description", required=True)
    args = parser.parse_args()

    data = _load_log()
    rnd = _ensure_round(data, args.round_num)
    rnd["findings"].append(
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
    """Add a fix to a round (auto-creates the round if needed)."""
    parser = argparse.ArgumentParser(description="Add a fix")
    parser.add_argument("--round-num", type=int, required=True)
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--what-changed", required=True)
    parser.add_argument("--why", required=True)
    args = parser.parse_args()

    data = _load_log()
    rnd = _ensure_round(data, args.round_num)
    rnd["fixes"].append(
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
    """Add a skipped finding to a round (auto-creates the round if needed)."""
    parser = argparse.ArgumentParser(description="Add a skipped finding")
    parser.add_argument("--round-num", type=int, required=True)
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--severity", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()

    data = _load_log()
    rnd = _ensure_round(data, args.round_num)
    rnd["skipped"].append(
        {
            "finding_id": args.finding_id,
            "file": args.file,
            "severity": args.severity,
            "reason": args.reason,
        }
    )
    _save_log(data)
    print(json.dumps({"ok": True}))


def cmd_finalize():
    """Finalize the session: compute summary, print summary box, optionally render markdown."""
    parser = argparse.ArgumentParser(description="Finalize the session")
    parser.add_argument("--log", default="", help="Write markdown log to this path")
    args = parser.parse_args()

    data = _load_log()
    data["meta"]["completed_at"] = datetime.now(timezone.utc).isoformat()
    data["summary"] = {
        "rounds_completed": len(data["rounds"]),
        "total_findings": sum(len(r.get("findings", [])) for r in data["rounds"]),
        "total_fixes": sum(len(r.get("fixes", [])) for r in data["rounds"]),
        "total_skipped": sum(len(r.get("skipped", [])) for r in data["rounds"]),
    }
    _save_log(data)

    path = session_log_path()
    summary = data["summary"]
    rows = [
        f"Rounds completed:  {summary.get('rounds_completed', 0)}",
        f"Total findings:    {summary.get('total_findings', 0)}",
        f"Total fixes:       {summary.get('total_fixes', 0)}",
        f"Total skipped:     {summary.get('total_skipped', 0)}",
        "",
        f"JSON log: {path}",
    ]
    print(box("Peer Review Complete", rows))

    if args.log:
        cmd_render_md(args.log)
        print(f"Markdown log: {args.log}")


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
            "Usage: change_log <init|add-finding|add-fix|add-skip|finalize|render-md> [args]",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = sys.argv[1]
    sys.argv = [f"change-log {cmd}"] + sys.argv[2:]

    if cmd == "init":
        cmd_init()
    elif cmd == "add-finding":
        cmd_add_finding()
    elif cmd == "add-fix":
        cmd_add_fix()
    elif cmd == "add-skip":
        cmd_add_skip()
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
