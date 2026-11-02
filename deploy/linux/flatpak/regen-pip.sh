#!/bin/sh
# Regenerate python3-dependencies.json from requirements.txt.
set -eu

cd "$(dirname "$0")"

MANIFEST=com.commandprompt.audax_data_manager.yml
GENERATOR_URL=https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/refs/heads/master/pip/flatpak-pip-generator.py

# Use the same SDK branch as the manifest, so that the wheels fit its Python.
RUNTIME_VERSION=$(sed -n "s/^runtime-version: '\(.*\)'$/\1/p" "$MANIFEST")
test -n "$RUNTIME_VERSION"

# Download the generator and install its Python packages in a temporary folder.
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR:?}"' EXIT
wget -q -O "$TMP_DIR/flatpak-pip-generator.py" "$GENERATOR_URL"
python3 -m venv "$TMP_DIR/venv"
"$TMP_DIR/venv/bin/pip" install -q --disable-pip-version-check requirements-parser packaging

"$TMP_DIR/venv/bin/python" "$TMP_DIR/flatpak-pip-generator.py" \
        --runtime="org.freedesktop.Sdk//$RUNTIME_VERSION" \
        --requirements-file=../../../requirements.txt \
        --ignore-pkg=psycopg2,pgspecial \
        --prefer-wheels=cryptography,bcrypt,pymssql \
        --wheel-arches=x86_64 \
        --output=python3-dependencies
