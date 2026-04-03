#!/usr/bin/env python3
"""Discover available checks by scanning references/checks/ for .md files."""
import json
import os
from pathlib import Path

CHECKS_DIR = Path(__file__).parent.parent / "skills" / "peer-review" / "references" / "checks"


def get_available_checks():
    """Return sorted list of check names (filenames without .md)."""
    if not CHECKS_DIR.is_dir():
        return []
    return sorted(p.stem for p in CHECKS_DIR.glob("*.md"))


def load_check(name):
    """Load a check's description from its .md file."""
    path = (CHECKS_DIR / f"{name}.md").resolve()
    if not str(path).startswith(str(CHECKS_DIR.resolve())):
        raise ValueError(f"Invalid check name: {name}")
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def main():
    checks = get_available_checks()
    print(json.dumps({"checks": checks}))


if __name__ == "__main__":
    main()
