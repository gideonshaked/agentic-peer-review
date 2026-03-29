#!/usr/bin/env python3
"""Render the audit prompt template with provided variables."""
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from scripts.list_checks import load_check

PROMPTS_DIR = Path(__file__).parent / "prompts"


def main():
    data = json.load(sys.stdin)

    # Resolve check names to {name, description} dicts
    check_names = data.get("checks", [])
    if isinstance(check_names, list) and check_names and isinstance(check_names[0], str):
        data["checks"] = [
            {"name": name, "description": load_check(name)}
            for name in check_names
        ]

    env = Environment(loader=FileSystemLoader(PROMPTS_DIR), keep_trailing_newline=True)
    template = env.get_template("audit.j2")
    print(template.render(data))


if __name__ == "__main__":
    main()
