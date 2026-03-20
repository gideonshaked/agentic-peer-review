#!/usr/bin/env python3
"""Render the audit prompt template with provided variables."""
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

PROMPTS_DIR = Path(__file__).parent / "prompts"


def main():
    data = json.load(sys.stdin)
    env = Environment(loader=FileSystemLoader(PROMPTS_DIR), keep_trailing_newline=True)
    template = env.get_template("audit.j2")
    print(template.render(data))


if __name__ == "__main__":
    main()
