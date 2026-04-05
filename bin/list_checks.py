"""CLI wrapper for listing available checks."""

import json

from bin.lib.checks import get_available_checks


def main():
    checks = get_available_checks()
    print(json.dumps({"checks": checks}))


if __name__ == "__main__":
    main()
