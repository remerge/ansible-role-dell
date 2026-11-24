#!/usr/bin/env python3
"""Find the newest Dell DSU release and the newest iSM installer in it.

Prints key=value lines in GitHub Actions output format. update=false means the
role already pins the newest release, the release's repodata is incomplete, or
Dell is unreachable; warnings go to stderr.

Usage: bin/dell-latest-release.py [--repo URL]
"""

import argparse
import gzip
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROLE_DIR = Path(__file__).resolve().parent.parent
REPOS = ["os_independent", "os_dependent/RHEL9_64"]
ISM_SUMMARY = "iDRAC Service Module Installer"


def warn(message: str) -> None:
    print(f"::warning::{message}", file=sys.stderr)


def fetch(url: str, attempts: int = 5) -> bytes | None:
    """Return the body of url, None on 404; raise ConnectionError after retries."""
    error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            error = e
        except OSError as e:
            error = e
        print(
            f"attempt {attempt}/{attempts} for {url} failed: {error}", file=sys.stderr
        )
        if attempt < attempts:
            time.sleep(10 * attempt)
    raise ConnectionError(f"{url}: {error}")


def as_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def output(**values: str) -> None:
    for key, value in values.items():
        print(f"{key}={value}")


def current_release() -> str:
    text = (ROLE_DIR / "vars/main.yml").read_text()
    match = re.search(r'^dell_repo_version: "(DSU_[\d.]+)"$', text, re.MULTILINE)
    if not match:
        sys.exit("dell_repo_version not found in vars/main.yml")
    return match.group(1)


def newest_ism(primary: str) -> dict[str, str]:
    packages = []
    for package in re.findall(r"<package .*?</package>", primary, re.DOTALL):
        if ISM_SUMMARY not in package:
            continue
        checksum = re.search(
            r'<checksum type="(sha256|sha512)"[^>]*>([0-9a-f]+)<', package
        )
        name = re.search(r"<name>([^<]+)</name>", package)
        version = re.search(r'<version [^>]*ver="([^"]+)"', package)
        location = re.search(r'<location href="([^"]+)"', package)
        if not (checksum and name and version and location):
            sys.exit(f"cannot parse iSM package metadata:\n{package}")
        packages.append(
            {
                "name": name.group(1),
                "version": version.group(1),
                "location": location.group(1),
                "checksum_type": checksum.group(1),
                "checksum": checksum.group(2),
            }
        )
    if not packages:
        sys.exit(f"no package with summary '{ISM_SUMMARY}' found")
    return max(packages, key=lambda p: as_tuple(p["version"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", default="https://linux.dell.com/repo")
    args = parser.parse_args()
    base = f"{args.repo}/hardware"

    current = current_release()
    try:
        index = fetch(f"{base}/")
        if index is None:
            sys.exit(f"{base}/ not found")
        latest = max(
            set(re.findall(r"DSU_\d+\.\d+\.\d+", index.decode())), key=as_tuple
        )
        print(f"current {current}, latest {latest}", file=sys.stderr)
        if as_tuple(latest) <= as_tuple(current):
            output(update="false")
            return

        # A release directory can appear before its repodata is complete.
        for repo in REPOS:
            if fetch(f"{base}/{latest}/{repo}/repodata/repomd.xml") is None:
                warn(f"{latest}/{repo} has no repodata yet")
                output(update="false")
                return

        primary = fetch(f"{base}/{latest}/os_independent/repodata/primary.xml.gz")
        if primary is None:
            sys.exit(f"{latest}/os_independent has no primary.xml.gz")
    except ConnectionError as e:
        warn(f"{args.repo} unreachable, retry on the next run: {e}")
        output(update="false")
        return

    ism = newest_ism(gzip.decompress(primary).decode())
    print(f"newest iSM installer: {ism['name']}", file=sys.stderr)

    output(
        update="true",
        dell_repo_version=latest,
        ism_version=ism["version"],
        ism_name=ism["name"],
        systems_management_version=ism["name"].removeprefix(
            "Systems-Management_Application_"
        ),
        ism_url=f"{base}/{latest}/os_independent/{ism['location']}",
        ism_checksum_type=ism["checksum_type"],
        ism_checksum=ism["checksum"],
    )


if __name__ == "__main__":
    main()
