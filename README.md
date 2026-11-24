# Ansible Role for Dell

Sets up Dell PowerEdge hosts running AlmaLinux 9 for firmware updates and
in-band iDRAC access.

```yaml
# requirements.yml
roles:
  - name: remerge.dell
    src: https://github.com/remerge/ansible-role-dell
    version: "26.11.23"
```

```yaml
# playbook
- hosts: dell_servers
  become: true
  roles:
    - role: remerge.dell
```

## What the Role Does

1. **Repositories:** adds Dell's Dell System Update (DSU) repositories,
   pinned to one release (`dell_repo_version`), and imports Dell's GPG keys
   from the `distribution-gpg-keys` package so the repositories verify without
   reaching linux.dell.com.
2. **Tools:** installs `dell-system-update` (the `dsu` command),
   `dsucatalog`, `srvadmin-idracadm7` and `perccli` (linked to
   `/usr/bin/perccli`), and stages the public keys `dsu` needs to verify the
   catalogs it downloads.
3. **iDRAC Service Module (iSM):** installs the pinned iSM installer, unpacks
   it, installs its `dcism` and `dcism-osc` RPMs, and starts `dcismeng`.

The role does not flash firmware; run `dsu` on a host for that.

## Variables

| Variable                             | Where               | Meaning                                                                                |
| ------------------------------------ | ------------------- | -------------------------------------------------------------------------------------- |
| `dell_repo_base_urls`                | `defaults/main.yml` | Base URLs of Dell's Linux repository, tried in order. Defaults to linux.dell.com only. |
| `dell_repo_version`                  | `vars/main.yml`     | The pinned DSU release, e.g. `DSU_26.11.23`.                                           |
| `systems_management_version`         | `vars/main.yml`     | The pinned iSM installer package.                                                      |
| `dcism_version`, `dcism_osc_version` | `vars/main.yml`     | The RPM versions inside that installer.                                                |

linux.dell.com is often down, so list mirrors after it in your inventory.
dnf moves to the next URL when a download fails. Every URL must carry the
pinned DSU release, and mirrors usually get a new release a day or two after
Dell.

```yaml
dell_repo_base_urls:
  - https://linux.dell.com/repo
  - https://ftp.gwdg.de/pub/linux/dell/repo
  - https://mirror.chpc.utah.edu/pub/linux.dell.com/repo
```

The values in `vars/main.yml` belong together and are not meant to be
overridden; they change through update pull requests.

## Updates

The `dell-update` workflow runs daily. When linux.dell.com has a DSU release
newer than `dell_repo_version`, it picks the newest iSM installer in it,
verifies the installer's checksum and Dell's signature, unpacks it to read the
`dcism` versions, and opens a pull request from `no-ticket/dell-update` that
updates all four values in `vars/main.yml`.

That pull request is opened with the workflow's token, so pre-commit does not
start on its own: close and reopen it to run the checks. Run the role on one
Dell host before merging it.

The scripts behind the workflow also run by hand:

| Script                       | Purpose                                                                                                                                                    |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bin/dell-latest-release.py` | Finds the newest DSU release and iSM installer on linux.dell.com.                                                                                          |
| `bin/dell-ism-versions.sh`   | Downloads, verifies and unpacks an iSM installer and prints its `dcism` versions. Linux only; runs the installer with `sudo`, so use a disposable machine. |
| `bin/dell-update-vars.py`    | Writes new versions into `vars/main.yml`.                                                                                                                  |

Each prints `key=value` lines on standard output and logs to standard error.

## Releases

Releases are tagged with the DSU release they pin (`26.11.23`); a change to
the role on the same DSU release gets a suffix (`26.11.23.1`). To release,
run `make release`, which starts the `release` workflow on `main` (also
available in the Actions tab). It picks the next tag with
`bin/dell-next-release.py`, refuses when `main` is already released, and
creates the release with GitHub's generated notes. Hosts get a new release
once the `version` in the requirements file moves to it.

## Development

Run `make install` once, then `make check` for the formatters and linters
that pre-commit runs in CI.
