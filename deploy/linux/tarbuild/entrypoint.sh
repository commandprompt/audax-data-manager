#!/bin/bash
set -e
# Checking environment
echo "REPO=$REPO"
echo "BRANCH=$BRANCH"
echo "VERSION=$VERSION"

# Cloning repo
git clone $REPO --depth 1 -b $BRANCH pgmanage

# Installing dependencies
cd pgmanage/
mkdir -p /deploy/pip-cache
pip3 install -r requirements.txt --cache-dir /deploy/pip-cache
pip3 install pyinstaller==5.13.2  --cache-dir /deploy/pip-cache

# if version is not provided, we use last tag from repository
if [ -z "$VERSION" ]
then
    # Fetching all tags from remote repository
    git fetch --all --tags

    # Getting last tag version
    export VERSION=$(git describe --tags $(git rev-list --tags --max-count=1))
fi

# Building server
cd pgmanage/

echo "Switching to Release Mode..."
sed -i -e 's/DEV_MODE = True/DEV_MODE = False/g' pgmanage/custom_settings.py
echo "Done."

echo "Switching to Desktop Mode... "
sed -i -e 's/DESKTOP_MODE = False/DESKTOP_MODE = True/g' pgmanage/custom_settings.py
echo "Done."

# setting up versions in custom_settins.py
sed -i "s/Dev/Audax Data Manager $VERSION/" pgmanage/custom_settings.py
sed -i "s/dev/$VERSION/" pgmanage/custom_settings.py

# building vite bundle
cd app/static/pgmanage_frontend/
npm install
npm run build
cd $HOME/pgmanage/pgmanage/

# Do a small clean-up
echo "Removing sass and map files"
find ./ -name "*.map" -delete
find ./ -name "*.scss" -delete

rm -f audaxdm.db audaxdm.log
touch audaxdm.db
pyinstaller process_executor-lin.spec
pyinstaller audaxdm-lin.spec
mv dist/* $HOME
rm -rf build dist
cd $HOME
cp process_executor audaxdm-server/

# temporarily disabled, we do not distribute the server-only version yet
# mkdir pgmanage-server_$VERSION
# cp pgmanage-server pgmanage-server_$VERSION/
# tar -czvf pgmanage-server_$VERSION-linux-x64.tar.gz pgmanage-server_$VERSION/
# mv pgmanage-server_$VERSION-linux-x64.tar.gz /tmp/

# Building app: tauri-cli makes an AppImage with the shell and WebKitGTK. The server is added
# afterwards: linuxdeploy would try to deploy the dependencies of its binaries and strip them.
cd $HOME/pgmanage/deploy/tauri/src-tauri
# the tag may carry a suffix (1.6.1-release), the app version has to be a plain semver
sed -i "s/\"version\": \".*\"/\"version\": \"${VERSION%%-*}\"/" tauri.conf.json
cargo tauri build --bundles appimage -- --locked
cd target/release/bundle/appimage
mv ./*.AppImage shell.AppImage
./shell.AppImage --appimage-extract
mkdir -p "squashfs-root/usr/lib/Audax Data Manager"
cp -a $HOME/audaxdm-server "squashfs-root/usr/lib/Audax Data Manager/"
ARCH=x86_64 appimagetool squashfs-root /deploy/audaxdm-$VERSION.AppImage

# Building deb and rpm packages
cd $HOME/pgmanage/deploy/linux/pkgbuild
mkdir -p stage/audaxdm-app
cp $HOME/pgmanage/deploy/tauri/src-tauri/target/release/audaxdm-app stage/audaxdm-app/
cp -r $HOME/audaxdm-server stage/audaxdm-app/
cp $HOME/pgmanage/LICENSE stage/
nfpm pkg -p deb -t /deploy/
nfpm pkg -p rpm -t /deploy/
