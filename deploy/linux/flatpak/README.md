# Audax Data Manager Flatpak

## Requirements

- `flatpak` and the Flatpak builder: `flatpak install flathub org.flatpak.Builder`
- `flatpak-node-generator`:
  `pipx install "git+https://github.com/flatpak/flatpak-builder-tools.git#egg=flatpak_node_generator&subdirectory=node"`
- For `regen-pip.sh`: `python3` with the `venv` module (on Debian and Ubuntu system Python, install `python3-venv`), and `wget`

The runtime, the SDK and the Node 22 SDK extension (branch 25.08) are installed by the build command.

## Build and run

Run the commands from this folder:

```sh
flatpak run org.flatpak.Builder --disable-rofiles-fuse --force-clean --user --install --install-deps-from=flathub builddir com.commandprompt.audax_data_manager.yml
```

```sh
flatpak run com.commandprompt.audax_data_manager
```

You can also start the app from the application menu.

`--disable-rofiles-fuse` is necessary on hosts with FUSE 3.18 (for example Ubuntu 26.04). There, the Flatpak'd builder cannot mount `rofiles-fuse` and stops with
`fusermount: file descriptor 4 is not a socket`. The option is safe: `rofiles-fuse` only protects the build cache.

The manifest builds the app from git, from the `flatpak-build-prep` branch on GitHub. Only committed and pushed changes are in the build.
Thus commit and push the app changes, together with the regenerated `npm-sources.json` and `python3-dependencies.json`, before you build.
To test local commits before a push, temporarily set `url` of the git source to your clone, for example `file:///home/<user>/work/pgmanage`.

To build as the Flathub servers do (sandboxed, into the `repo` folder), use `flathub-build`, then check the result:

```sh
flatpak run --command=flathub-build org.flatpak.Builder --disable-rofiles-fuse --install com.commandprompt.audax_data_manager.yml
```

```sh
flatpak run --command=flatpak-builder-lint org.flatpak.Builder repo repo
```

## Regenerate the Python dependencies

Run the script when `requirements.txt` or `runtime-version` in the manifest changes:

```sh
./regen-pip.sh
```

The script downloads the newest `flatpak-pip-generator.py` from [flatpak-builder-tools](https://github.com/flatpak/flatpak-builder-tools) into a temporary folder.
It installs the generator's Python packages (`requirements-parser`, `packaging`) into a temporary virtual environment there, runs the generator, and then removes the folder.
The generator runs pip inside the SDK, so the first run can download the SDK.

- `psycopg2` needs `pg_config` to read its own metadata, and the SDK has no `pg_config`. Thus `psycopg2` and `pgspecial` (which needs `psycopg2`) are not in the generated file.
  The `python3-psycopg2` module in the manifest builds them against the bundled PostgreSQL 18, together with `click`.
  When the versions of these packages change, update their URLs and `sha256` values in that module by hand. Use the PyPI JSON API to get the values, for example `https://pypi.org/pypi/psycopg2/2.9.13/json`.
- `cryptography` and `bcrypt` need Rust to build from source, and `pymssql` needs FreeTDS. `--prefer-wheels` takes their manylinux wheels.

## Regenerate the npm sources

Run this command when `package-lock.json` changes:

```sh
flatpak-node-generator npm ../../../pgmanage/app/static/pgmanage_frontend/package-lock.json -o npm-sources.json
```

Every package in `package-lock.json` must have a `resolved` and an `integrity` field. The generator skips entries without them, and the offline `npm ci` then stops with `ENOTCACHED`.

Two parts of the `audaxdm` module are related to the four git dependencies (pev2, sql-autocomplete, antlr4ts-sql, vue-power-tree):

- `_PACOTE_NO_PREPARE_` stops npm from "preparing" these packages. Preparation installs their dev dependencies, which are not in the offline cache. The packages already contain their built files, so preparation is not necessary.
  The values must be the same as the `resolved` values of these packages in `package-lock.json`. When a git dependency moves to a different commit, update the value.
- pev2 runs `husky` (git hooks) as its `prepare` script. A stub `husky` (`flatpak-node/stub-bin/husky`) stands in for it during `npm ci`.

## Update to a new release

1. Make sure that the release tag contains the Flatpak changes:
   - `deploy/linux/pkgbuild/audaxdm-app.desktop`
   - `deploy/linux/flatpak/com.commandprompt.audax_data_manager.metainfo.xml` with a `<release>` entry for the new version (version, date and release-notes URL)
   - the PostgreSQL binary discovery in `/app/lib/postgresql/{v}/bin` (`pgmanage/app/models/main.py`)
   - the Flatpak data folder (`pgmanage/pgmanage-server.py`)
2. In the git source of the `audaxdm` module, replace `branch` with the release tag, its full commit hash and the update checker (see the comment in the manifest).
   Until you do this, the manifest lint reports `module-audaxdm-source-git-branch`.
3. Set `AUDAXDM_VERSION` in the `audaxdm` module to the new version.
4. Regenerate the Python dependencies and the npm sources if `requirements.txt` or `package-lock.json` changed.
5. Validate and build:

```sh
appstreamcli validate com.commandprompt.audax_data_manager.metainfo.xml
```

```sh
flatpak run --command=flatpak-builder-lint org.flatpak.Builder manifest com.commandprompt.audax_data_manager.yml
```

```sh
flatpak run org.flatpak.Builder --disable-rofiles-fuse --force-clean --user --install --install-deps-from=flathub builddir com.commandprompt.audax_data_manager.yml
```

```sh
flatpak run --command=flatpak-builder-lint org.flatpak.Builder builddir builddir
```

### PostgreSQL and NW.js

- The PostgreSQL and NW.js sources have `x-checker-data` for the Flatpak External Data Checker. For a manual update, change the URL and take the `sha256` from the `.sha256` file next to the PostgreSQL tarball, or from `SHASUMS256.txt` for NW.js.
- Test each NW.js update before you use it. The `stable` value of `https://nwjs.io/versions.json` can be newer than the tested version.
- To add a PostgreSQL major version, copy a `postgresql-<major>` module and set `PG_MAJOR`. Also add the version to `SUPPORTED_POSTGRES_VERSIONS` in `pgmanage/pgmanage/settings.py`.
  If the new version is the newest, move the `post-install` commands from `postgresql-18` to it, and change `/app/lib/postgresql/18/bin` in the `python3-psycopg2` module.

## Debug

- Build until a module, without that module:

```sh
flatpak run org.flatpak.Builder --disable-rofiles-fuse --keep-build-dirs --stop-at=audaxdm builddir com.commandprompt.audax_data_manager.yml
```

- Open a shell in that build environment (SDK tools, no network, `/app` from the modules before it). `flatpak build` does not apply the `build-options` of the manifest, so set `PATH` and the `env` values by hand:

```sh
flatpak build --filesystem="$(git rev-parse --show-toplevel)" --build-dir="$(git rev-parse --show-toplevel)" builddir bash
```

- With `--keep-build-dirs`, the sources of a failed module stay in `.flatpak-builder/build/<module>-<n>`.
- Open a shell in the sandbox of the installed app. Add `--devel` to get the SDK tools (gdb, strace):

```sh
flatpak run --command=bash com.commandprompt.audax_data_manager
```

- The server log is `~/.var/app/com.commandprompt.audax_data_manager/data/audaxdm-app/audaxdm.log`.

`--build-shell` and `--run` of `flatpak-builder` do not work with the Flatpak'd builder on hosts with FUSE 3.18.

## Notes

- **User data:** the Flatpak keeps its data in `~/.var/app/com.commandprompt.audax_data_manager/data/audaxdm-app`. It does not use `~/.audaxdm` of the AppImage. To keep AppImage connections, copy `~/.audaxdm/audaxdm-app` to that folder before the first start.
- **File access:** the app has access to the home folder (`--filesystem=home`). For other locations, such as `/mnt` or `/media`, the user can add access:

```sh
flatpak override --user --filesystem=host com.commandprompt.audax_data_manager
```

- **PostgreSQL tools:** the app contains `pg_dump`, `pg_dumpall`, `pg_restore` and `psql` for PostgreSQL 13–18 in `/app/lib/postgresql/<major>/bin`, and the 18 tools in `/app/bin`. Host PostgreSQL binaries do not work in the sandbox, also when a host path is set in Settings.
- **Architectures:** x86_64 only.
- **Runtime:** the manifest uses runtime 25.08. Flathub requires the newest runtime (26.08) for a new submission. To change it, set `runtime-version`, then run `./regen-pip.sh` again. The Node 22 SDK extension is also available for 26.08.
