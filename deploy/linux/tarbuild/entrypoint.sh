#!/bin/bash
set -e
# Checking environment
echo "REPO=$REPO"
echo "BRANCH=$BRANCH"
echo "VERSION=$VERSION"
echo "DEBUG=$DEBUG"

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

# if change nwjs and build options for debug
if [ "$DEBUG" == false ]
then
    NWJS_URL='https://dl.nwjs.io/v0.114.0/nwjs-v0.114.0-linux-x64.tar.gz'
    NWJS_ARCHIVE='nwjs-v0.114.0-linux-x64.tar.gz'
    NWJS_DIR='nwjs-v0.114.0-linux-x64'
else
    NWJS_URL='https://dl.nwjs.io/v0.114.0/nwjs-sdk-v0.114.0-linux-x64.tar.gz'
    NWJS_ARCHIVE='nwjs-sdk-v0.114.0-linux-x64.tar.gz'
    NWJS_DIR='nwjs-sdk-v0.114.0-linux-x64'
    echo "*****************************************************"
    echo "*********** BUILDING DEBUG CONFIGURATION ************"
    echo "*****************************************************"
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

# temporarily disabled, we do not distribute the server-only version yet
# mkdir pgmanage-server_$VERSION
# cp pgmanage-server pgmanage-server_$VERSION/
# tar -czvf pgmanage-server_$VERSION-linux-x64.tar.gz pgmanage-server_$VERSION/
# mv pgmanage-server_$VERSION-linux-x64.tar.gz /tmp/

# Building app
cd /deploy
curl -C - -LO $NWJS_URL
# get appimagetool
curl -C - -LO https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage && chmod +x /deploy/appimagetool-x86_64.AppImage

cd -
tar -xzvf /deploy/$NWJS_ARCHIVE
mv $NWJS_DIR audaxdm-app_$VERSION
cd audaxdm-app_$VERSION

cp -r $HOME/audaxdm-server ./
cp $HOME/process_executor ./audaxdm-server/
# copy index.html .desktop and pgmanage_icon.png to the output dir
cp $HOME/pgmanage/deploy/app/* .
# adjust the version
sed -i "s/version_placeholder/v$VERSION/" index.html
sed -i "s/X-AppImage-Version=dev/X-AppImage-Version=$VERSION/" audaxdm.desktop
# rename nwjs runtime as audaxdm-app
mv nw audaxdm-app && ln -s ./audaxdm-app AppRun
cd $HOME
/deploy/appimagetool-x86_64.AppImage --appimage-extract-and-run audaxdm-app_$VERSION/ audaxdm-$VERSION.AppImage
# tar -czvf pgmanage-app_$VERSION-linux-x64.tar.gz pgmanage-app_$VERSION/
# mv pgmanage-app_$VERSION-linux-x64.tar.gz /tmp/
mv audaxdm-$VERSION.AppImage /deploy

# Building deb and rpm packages
cd $HOME/pgmanage/deploy/linux/pkgbuild
mkdir stage
mv $HOME/audaxdm-app_$VERSION stage/audaxdm-app
# the nwjs archive gives mode 0700 to this directory
chmod 755 stage/audaxdm-app
cp $HOME/pgmanage/LICENSE stage/
nfpm pkg -p deb -t /deploy/
nfpm pkg -p rpm -t /deploy/