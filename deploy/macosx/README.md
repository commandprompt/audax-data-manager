# PgManage macOS Build

The following software should be installed prior to running the build script:

Official Python 3.11.* macOs release

- Homebrew
- Node.js 22 or newer
- npm
- PostgreSQL client library with `pg_config` on `PATH` (e.g. `brew install libpq`), needed to compile psycopg2 (also for the arm64 build, where it is replaced afterwards)

## Building
1. Simply run in command line deploy script:
```
./deploy.sh [pgmanage_version] [branch_name]
```
- `pgmanage_version`(*optional*): The version number that will be added to bundle and `.dmg` file.
If not provided, the script defaults to the last version tag from Git repository.
- `branch_name`(*optional*): The Git branch to build from.If not provided, the script defaults to the `master` branch.

- `architecture`(*optional*): `x64` (default) or `arm64`. Both can be built on an Intel Mac.

### Apple Silicon (arm64) build
arm64 is cross-compiled on an Intel Mac. Additionally to the above, install the universal2 [Python 3.11.9](https://www.python.org/downloads/release/python-3119/) from python.org (the last 3.11 release with a binary installer), since PyInstaller can target arm64 only from a universal2 Python.

`universal2.py` replaces the installed packages that have no arm64 slice with universal2 builds (psycopg2 becomes psycopg2-binary), and the script fails if any binary in the server bundle is not arm64. The app bundle is ad-hoc signed, because arm64 binaries can't run unsigned. The SQL Server driver (pymssql) is available on macOS 14 or newer only.

Output: `audaxdm-<version>_mac_x64.dmg` or `audaxdm-<version>_mac_arm64.dmg`.

### Signing and notarization
Controlled by environment variables:

- `SIGN_IDENTITY`: a "Developer ID Application" identity (name or hash). The app is signed by `sign.sh` with the hardened runtime and `entitlements.plist`, and the `.dmg` is signed too. Without it, arm64 builds are signed ad-hoc and x64 builds are unsigned.
- `KEYCHAIN`: (*optional*) keychain to look the identity up in. It must be unlocked (`security unlock-keychain`), and `security set-key-partition-list` must have been run for it, otherwise `codesign` fails with `errSecInternalComponent`.
- `NOTARY_PROFILE`: (*optional*, requires `SIGN_IDENTITY`) profile created with `xcrun notarytool store-credentials`. The app and then the `.dmg` are submitted to Apple and stapled.

```
export SIGN_IDENTITY="Developer ID Application: Company (TEAMID)"
export NOTARY_PROFILE=audaxdm-notary
./deploy.sh 1.6.2 master arm64
```

A self-signed identity is enough to test the signing flow, but Gatekeeper rejects it and notarization needs a real Developer ID.

This will create the python virtual environment and install all the required python modules mentioned in the requirements file using pip, build the runtime code and finally create the app bundle and the DMG in `./release_$pgmanage_version` directory.