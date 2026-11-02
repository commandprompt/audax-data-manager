# Audax Data Manager Flatpak

Release and maintenance steps for the Flatpak package `com.commandprompt.audax_data_manager`. Run the commands from this folder.

## Release a new version

1. Before you create the release tag, add a `<release>` entry for the new version (version, date and release-notes URL) to `com.commandprompt.audax_data_manager.metainfo.xml`. Then validate the file:

```sh
appstreamcli validate com.commandprompt.audax_data_manager.metainfo.xml
```

2. If `requirements.txt` or `package-lock.json` changed in the release, regenerate the dependency files from a checkout of the release tag (see the next sections).
   If the release uses a different NW.js version (`NWJS_URL` in `deploy/linux/tarbuild/entrypoint.sh`), update the `nwjs` source.
3. Set `AUDAXDM_VERSION` in the `audaxdm` module to the new version.
4. Push the changes to a pull request in the Flathub repo.


## Regenerate the Python dependencies

Run the script when `requirements.txt` or `runtime-version` in the manifest changes:

```sh
./regen-pip.sh
```

## Regenerate the npm sources

Run this command when `package-lock.json` changes:

```sh
flatpak-node-generator npm ../../../pgmanage/app/static/pgmanage_frontend/package-lock.json -o npm-sources.json
```

Every package in `package-lock.json` must have a `resolved` and an `integrity` field. The generator skips entries without them, and the offline `npm ci` then stops with `ENOTCACHED`.

