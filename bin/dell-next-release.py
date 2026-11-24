#!/usr/bin/env python3
"""Print the next release tag for the role as tag=<tag>.

Releases are tagged with the pinned DSU release (DSU_26.11.23 -> 26.11.23); a
later release on the same DSU release gets a suffix (26.11.23.1, .2, ...).
Exits with an error when HEAD is already tagged, so there is nothing new to
release. Needs the repository's tags (git fetch --tags).

Usage: bin/dell-next-release.py
"""

import re
import subprocess
import sys
from pathlib import Path

ROLE_DIR = Path(__file__).resolve().parent.parent


def git(*args: str) -> list[str]:
    result = subprocess.run(
        ["git", *args], cwd=ROLE_DIR, capture_output=True, text=True, check=True
    )
    return result.stdout.split()


def main() -> None:
    text = (ROLE_DIR / "vars/main.yml").read_text()
    match = re.search(r'^dell_repo_version: "DSU_([\d.]+)"$', text, re.MULTILINE)
    if not match:
        sys.exit("dell_repo_version not found in vars/main.yml")
    base = match.group(1)

    if tagged := git("tag", "--points-at", "HEAD"):
        sys.exit(f"HEAD is already released as {', '.join(tagged)}")

    suffixes = []
    for tag in git("tag", "--list", f"{base}*"):
        if tag == base:
            suffixes.append(0)
        elif m := re.fullmatch(rf"{re.escape(base)}\.(\d+)", tag):
            suffixes.append(int(m.group(1)))

    tag = f"{base}.{max(suffixes) + 1}" if suffixes else base
    print(f"tag={tag}")


if __name__ == "__main__":
    main()
