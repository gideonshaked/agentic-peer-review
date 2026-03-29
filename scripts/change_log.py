#!/usr/bin/env python3
"""Manage the structured JSON change log for peer review sessions.

Subcommands:
    init        Create a new change log temp file
    add-round   Append a round's data to the log
    finalize    Compute summary, set completed_at, print JSON
    render-md   Render the finalized JSON as a markdown log file
"""
import json
import os
import sys
from datetime import datetime, timezone


def _log_path():
    """Generate a unique temp file path."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"/tmp/peer-review-{os.getpid()}-{ts}.json"


def cmd_init():
    """Create a new change log. Reads metadata JSON from stdin."""
    meta = json.load(sys.stdin)
    path = _log_path()
    data = {
        "meta": {
            "agent": meta.get("agent", ""),
            "max_rounds": meta.get("max_rounds", 0),
            "focus": meta.get("focus", ""),
            "message": meta.get("message", ""),
            "worktree": meta.get("worktree", False),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": "",
            "project": meta.get("project", {}),
        },
        "rounds": [],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(json.dumps({"log_file": path}))


def cmd_add_round(log_file):
    """Append a round to the log. Reads round JSON from stdin."""
    round_data = json.load(sys.stdin)
    with open(log_file, encoding="utf-8") as f:
        data = json.load(f)
    data["rounds"].append(round_data)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(json.dumps({"ok": True}))


def cmd_finalize(log_file):
    """Compute summary, set completed_at, print finalized JSON."""
    with open(log_file, encoding="utf-8") as f:
        data = json.load(f)
    data["meta"]["completed_at"] = datetime.now(timezone.utc).isoformat()
    data["summary"] = {
        "rounds_completed": len(data["rounds"]),
        "total_findings": sum(len(r.get("findings", [])) for r in data["rounds"]),
        "total_fixes": sum(len(r.get("fixes", [])) for r in data["rounds"]),
        "total_skipped": sum(len(r.get("skipped", [])) for r in data["rounds"]),
    }
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(json.dumps(data))


def cmd_render_md(log_file, output_path):
    """Render the finalized JSON as a markdown file."""
    with open(log_file, encoding="utf-8") as f:
        data = json.load(f)

    meta = data["meta"]
    lines = [
        f"# Peer Review Log",
        "",
        f"- **Agent:** {meta['agent']}",
        f"- **Project:** {meta['project'].get('language', 'unknown')}"
        + (f"/{meta['project']['framework']}" if meta['project'].get('framework') else ""),
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
        print("Usage: change_log <init|add-round|finalize|render-md> [args]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "init":
        cmd_init()
    elif cmd == "add-round":
        if len(sys.argv) < 3:
            print("Usage: change_log add-round <log_file>", file=sys.stderr)
            sys.exit(1)
        cmd_add_round(sys.argv[2])
    elif cmd == "finalize":
        if len(sys.argv) < 3:
            print("Usage: change_log finalize <log_file>", file=sys.stderr)
            sys.exit(1)
        cmd_finalize(sys.argv[2])
    elif cmd == "render-md":
        if len(sys.argv) < 3:
            print("Usage: change_log render-md <log_file> --output <path>", file=sys.stderr)
            sys.exit(1)
        output_path = ""
        for i, arg in enumerate(sys.argv):
            if arg == "--output" and i + 1 < len(sys.argv):
                output_path = sys.argv[i + 1]
        if not output_path:
            print("--output <path> is required", file=sys.stderr)
            sys.exit(1)
        cmd_render_md(sys.argv[2], output_path)
    else:
        print(f"Unknown subcommand: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
