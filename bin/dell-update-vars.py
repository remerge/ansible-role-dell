#!/usr/bin/env python3
"""Set the Dell repository and iSM versions in vars/main.yml.

Usage: bin/dell-update-vars.py --dell-repo-version DSU_26.11.23 \
    --systems-management-version JDJH3_LN64_6.2.0.0_A00_04 \
    --dcism-version 6.2.0.0-1 --dcism-osc-version 8.2.0.0-1
"""

import argparse
import re
import sys
from pathlib import Path

VARS_FILE = Path(__file__).resolve().parent.parent / "vars/main.yml"
KEYS = [
    "dell_repo_version",
    "systems_management_version",
    "dcism_version",
    "dcism_osc_version",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for key in KEYS:
        parser.add_argument(f"--{key.replace('_', '-')}", required=True)
    parser.add_argument("--vars-file", type=Path, default=VARS_FILE)
    args = parser.parse_args()

    text = args.vars_file.read_text()
    for key in KEYS:
        value = getattr(args, key)
        if '"' in value or "\n" in value:
            sys.exit(f"invalid {key}: {value!r}")
        text, count = re.subn(
            rf'^{key}: ".*"$', f'{key}: "{value}"', text, flags=re.MULTILINE
        )
        if count != 1:
            sys.exit(f"{key} found {count} times in {args.vars_file}")
    args.vars_file.write_text(text)


if __name__ == "__main__":
    main()
