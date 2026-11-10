#!/bin/bash

set -e

VERSION=${1:?Usage: ./build_snap.sh [version]}
DEB=audaxdm-app_${VERSION}_amd64.deb

if [ ! -f "$DEB" ]; then
    echo "$DEB not found. Run ./deploy.sh $VERSION first."
    exit 1
fi

mkdir -p snap/local
cp "$DEB" snap/local/audaxdm-app.deb
cp ../../artwork/audax/audaxdm_256.png snap/local/audaxdm.png

snapcraft clean audaxdm
snapcraft pack
