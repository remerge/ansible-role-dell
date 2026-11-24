#!/usr/bin/env bash
# Download a Dell iSM installer RPM, verify it, unpack it, and print the dcism
# RPM versions it contains as key=value lines (GitHub Actions output format).
#
# Usage: bin/dell-ism-versions.sh URL CHECKSUM_TYPE CHECKSUM NAME
#   URL            the Systems-Management_Application_* RPM on linux.dell.com
#   CHECKSUM_TYPE  sha256 or sha512, from the repo metadata
#   CHECKSUM       the RPM's checksum from the repo metadata
#   NAME           the package name, e.g. Systems-Management_Application_JDJH3_LN64_6.2.0.0_A00_04
#
# Needs Linux with curl, gpg, rpm2cpio, cpio and sudo. The installer refuses to
# run without root, so it runs with sudo; use this only on a disposable machine.

set -euo pipefail

if [ $# -ne 4 ]; then
    sed -n '2,13s/^# \{0,1\}//p' "$0" >&2
    exit 2
fi

url=$1
checksum_type=$2
checksum=$3
name=$4

# Dell Inc., PGRE 2012 <PG_Release_Engineering@Dell.com>, signs the iSM
# installer (.BIN.sign), like dell-system-update itself.
key_fingerprint=42550ABD1E80D7C1BC0BAD851285491434D8786F
key_url="https://linux.dell.com/repo/pgp_pubkeys/0x${key_fingerprint: -16}.asc"

case $checksum_type in
sha256 | sha512) ;;
*)
    echo "unsupported checksum type: $checksum_type" >&2
    exit 2
    ;;
esac

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"

curl -fsSL --retry 5 --retry-delay 10 --retry-all-errors -m 600 -o ism.rpm "$url"
echo "$checksum  ism.rpm" | "${checksum_type}sum" -c - >&2
rpm2cpio ism.rpm | cpio -idm --quiet
bin="usr/libexec/dell_dup/$name.BIN"

export GNUPGHOME="$work/gnupg"
mkdir -m 700 "$GNUPGHOME"
curl -fsSL --retry 5 --retry-delay 10 --retry-all-errors -m 120 -o dell.asc "$key_url"
gpg --batch --quiet --import dell.asc
gpg --batch --with-colons --list-keys | grep -x "fpr:::::::::$key_fingerprint:" >/dev/null
gpg --batch --status-fd 1 --verify "$bin.sign" "$bin" |
    grep "^\[GNUPG:\] VALIDSIG $key_fingerprint " >/dev/null

chmod +x "$bin"
sudo "$bin" --extract "$work/extracted" >&2
sudo chown -R "$(id -u):$(id -g)" "$work"
find "$work/extracted" -name '*.rpm' -printf '%f\n' | sort >rpms.txt
cat rpms.txt >&2

dcism=$(sed -nE 's/^dcism-([0-9][^ ]*)\.el9\.x86_64\.rpm$/\1/p' rpms.txt)
dcism_osc=$(sed -nE 's/^dcism-osc-([0-9][^ ]*)\.rpm$/\1/p' rpms.txt)
if [ "$(echo "$dcism" | wc -w)" != 1 ] || [ "$(echo "$dcism_osc" | wc -w)" != 1 ]; then
    echo "::error::expected one dcism-*.el9.x86_64.rpm and one dcism-osc-*.rpm in $name" >&2
    exit 1
fi
echo "dcism_version=$dcism"
echo "dcism_osc_version=$dcism_osc"
