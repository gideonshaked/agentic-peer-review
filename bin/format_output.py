#!/usr/bin/env python3
"""Box-drawing formatted output helpers for peer review sessions."""

import json


def box(title, rows, width=None):
    """Render rows inside a box with a title bar."""
    all_lines = [title] + rows
    if width is None:
        width = max(len(line) for line in all_lines) + 4
    width = max(width, len(title) + 4)

    out = []
    out.append("┌" + "─" * (width - 2) + "┐")
    out.append("│ " + title.ljust(width - 4) + " │")
    out.append("├" + "─" * (width - 2) + "┤")
    for row in rows:
        out.append("│ " + row.ljust(width - 4) + " │")
    out.append("└" + "─" * (width - 2) + "┘")
    return "\n".join(out)


def simple_box(text, width=None):
    """Render a single line inside a box (no title bar)."""
    if width is None:
        width = len(text) + 4
    out = []
    out.append("┌" + "─" * (width - 2) + "┐")
    out.append("│ " + text.ljust(width - 4) + " │")
    out.append("└" + "─" * (width - 2) + "┘")
    return "\n".join(out)


def cmd_settings(json_str):
    """Render settings box from parse_args JSON."""
    data = json.loads(json_str)

    all_checks = data.get("all_checks", [])
    active_checks = data.get("checks", all_checks)
    total = len(all_checks)
    active = len(active_checks)

    checks_label = ", ".join(c.replace("-", " ") for c in active_checks)

    instructions = data.get("instructions", "")
    if instructions:
        instr_line = f'"{instructions}" (in addition to checks above)'
    else:
        instr_line = "none (using default checks only)"

    rows = [
        f"Agent:        {data.get('agent', '')}",
        f"Max rounds:   {data.get('max_rounds', '')}",
        f"Focus:        {data.get('focus') or 'entire codebase'}",
        f"Timeout:      {data.get('timeout', 300)}s",
        f"Worktree:     {'yes' if data.get('worktree') else 'no'}",
        f"Log:          {data.get('log') or 'none'}",
        "",
        f"Checks ({active} of {total}):",
        f"  {checks_label}",
        "",
        "Instructions:",
        f"  {instr_line}",
    ]

    print(box("Peer Review Settings", rows))


def cmd_round_header(round_num, total_rounds, elapsed=None):
    """Render round header box with optional time estimate."""
    text = f"Round {round_num}/{total_rounds}"

    if round_num >= 3 and elapsed is not None:
        avg_per_round = elapsed / (round_num - 1)
        remaining_seconds = avg_per_round * (total_rounds - round_num + 1)
        hours = int(remaining_seconds // 3600)
        minutes = int((remaining_seconds % 3600) // 60)
        seconds = int(remaining_seconds % 60)
        if hours > 0:
            text += f" (est. {hours}h {minutes:02d}m remaining)"
        else:
            text += f" (est. {minutes:02d}:{seconds:02d} remaining)"

    print(simple_box(text))
