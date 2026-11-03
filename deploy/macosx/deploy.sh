#!/bin/bash

# Build script to create Mac App Bundle for pgmanage

# Exit when any command fails
set -e -e

APP_VERSION="$1"
REPO="https://github.com/commandprompt/audax-data-manager"
BRANCH="${2:-master}"
DEPLOY_DIR=$(pwd)
TEMP_DIR=$DEPLOY_DIR/tmp

# if version is not provided, we use last tag from repository
if [ -z "$APP_VERSION" ]
then
    # Fetch all tags from remote repository
    git fetch --all --tags

    # Get last tag version
    APP_VERSION=$(git describe --tags $(git rev-list --tags --max-count=1))
fi

# Target architecture: x64 (default) or arm64. arm64 is cross-compiled, so this also works on an Intel Mac
ARCH="${3:-x64}"
case "$ARCH" in
    x64|arm64) ;;
    *) echo "Unsupported architecture: $ARCH (use x64 or arm64)"; exit 1 ;;
esac

NWJS_URL="https://dl.nwjs.io/v0.114.0/nwjs-v0.114.0-osx-$ARCH.zip"
NWJS_ARCHIVE="nwjs-v0.114.0-osx-$ARCH.zip"
NWJS_DIR="nwjs-v0.114.0-osx-$ARCH"

APP_LONG_VERSION=audaxdm-$APP_VERSION
APP_NAME='Audax Data Manager'
RELEASE_DIR=$DEPLOY_DIR/release_$APP_VERSION

rm -rf $RELEASE_DIR $TEMP_DIR
mkdir $RELEASE_DIR $TEMP_DIR

cd $TEMP_DIR

echo "cloning repository $REPO"
git clone $REPO --depth 1 -b $BRANCH .

if [ "$ARCH" = "arm64" ]
then
    # pyenv builds Python for the host architecture only, the universal2 python.org installer
    # (3.11.9 is the last 3.11 release with a binary installer) can be targeted at arm64 by PyInstaller
    PYTHON_EXE=/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11
    export PYINSTALLER_TARGET_ARCH=arm64
else
    # Install pyenv to manage specific python version
    brew update && brew upgrade
    brew install pyenv
    brew install xz

    # Install Python 3.11.15 and create virtual environment
    env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.11.15 --skip-existing

    pyenv local 3.11.15
    PYTHON_EXE=$(pyenv which python)
fi

$PYTHON_EXE -m venv venv
source venv/bin/activate

# Install all required libraries
echo "installing python dependencies"
pip3 install -r requirements.txt
pip3 install pyinstaller==5.13.2

if [ "$ARCH" = "arm64" ]
then
    # replaces packages that have no arm64 slice with universal2 builds
    pip3 install delocate
    python $DEPLOY_DIR/universal2.py
fi

cd pgmanage/

echo -n "Switching to Release Mode..."
sed -i -e 's/DEV_MODE = True/DEV_MODE = False/g' pgmanage/custom_settings.py
echo "Done."

echo -n "Switching to Desktop Mode... "
sed -i -e 's/DESKTOP_MODE = False/DESKTOP_MODE = True/g' pgmanage/custom_settings.py
echo "Done."

# building vite bundle
cd app/static/pgmanage_frontend/

echo "installing javascript dependencies"
npm install

echo "building vite bundle"
npm run build

cd $TEMP_DIR/pgmanage

# Do a small clean-up
echo -n "Removing sass and map files"
find ./ -name "*.map" -delete
find ./ -name "*.scss" -delete

touch audaxdm.db

# set up versions in custom_settins.py
sed -i '' "s/Dev/Audax Data Manager $APP_VERSION/" pgmanage/custom_settings.py
sed -i '' "s/dev/$APP_VERSION/" pgmanage/custom_settings.py

echo "running pyinstaller"
pyinstaller audaxdm-mac.spec
pyinstaller process_executor-mac.spec

mkdir audaxdm-server 
# python.org framework builds name the library "Python"
LIBPYTHON=libpython3.11.dylib
if [ "$ARCH" = "arm64" ]
then
    LIBPYTHON=Python
fi

echo "Removing signature from $LIBPYTHON library"
codesign --remove-signature dist/audaxdm-server/$LIBPYTHON
mv dist/process_executor audaxdm-server/
mv dist/audaxdm-server/* audaxdm-server/

if [ "$ARCH" = "arm64" ]
then
    echo 'Checking that all binaries are arm64'
    find audaxdm-server -type f | while read -r f
    do
        archs=$(lipo -archs "$f" 2>/dev/null) || continue
        [ "$archs" = "arm64" ] || { echo "unexpected architecture ($archs): $f"; exit 1; }
    done
fi

cd $DEPLOY_DIR

curl -C - -LO $NWJS_URL
unzip $NWJS_ARCHIVE -d $TEMP_DIR

cd $TEMP_DIR
mv $NWJS_DIR/nwjs.app $APP_LONG_VERSION.app

mkdir $APP_LONG_VERSION.app/Contents/Resources/app.nw
mv pgmanage/audaxdm-server $APP_LONG_VERSION.app/Contents/Resources/app.nw/

cp deploy/app/* $APP_LONG_VERSION.app/Contents/Resources/app.nw/
sed -i '' "s/version_placeholder/v$APP_VERSION/" $APP_LONG_VERSION.app/Contents/Resources/app.nw/index.html

# Replace default icons with pgmanage icon
cp $DEPLOY_DIR/mac-icon.icns $APP_LONG_VERSION.app/Contents/Resources/app.icns
cp $DEPLOY_DIR/mac-icon.icns $APP_LONG_VERSION.app/Contents/Resources/document.icns

# removes unnecessary keys from Info.plist
plutil -remove ASWebAuthenticationSessionWebBrowserSupportCapabilities $APP_LONG_VERSION.app/Contents/Info.plist
plutil -remove CFBundleDocumentTypes $APP_LONG_VERSION.app/Contents/Info.plist
plutil -remove CFBundleURLTypes $APP_LONG_VERSION.app/Contents/Info.plist
plutil -remove UTExportedTypeDeclarations $APP_LONG_VERSION.app/Contents/Info.plist
plutil -remove UTImportedTypeDeclarations $APP_LONG_VERSION.app/Contents/Info.plist

# Set up correct application name
plutil -replace CFBundleName -string "$APP_NAME" $APP_LONG_VERSION.app/Contents/Info.plist

plutil -replace CFBundleDisplayName -string "$APP_NAME" $APP_LONG_VERSION.app/Contents/Info.plist

plutil -replace CFBundleExecutable -string "$APP_NAME" $APP_LONG_VERSION.app/Contents/Info.plist

plutil -replace CFBundleShortVersionString -string $APP_VERSION $APP_LONG_VERSION.app/Contents/Info.plist

echo CFBundleDisplayName = \"$APP_NAME\" >> $APP_LONG_VERSION.app/Contents/Resources/el.lproj/InfoPlist.strings

# rename nwjs executable
mv $APP_LONG_VERSION.app/Contents/MacOS/nwjs "$APP_LONG_VERSION.app/Contents/MacOS/$APP_NAME"

mv $APP_LONG_VERSION.app "$RELEASE_DIR/$APP_NAME.app"

# The edits above invalidated the signatures, so the app is signed again.
# SIGN_IDENTITY: Developer ID Application identity (name or hash), optionally KEYCHAIN to look it up in.
# Without it arm64 builds are signed ad-hoc (arm64 binaries must be signed to run), x64 builds stay unsigned.
# NOTARY_PROFILE: notarytool keychain profile (xcrun notarytool store-credentials), requires SIGN_IDENTITY.
if [ -z "$SIGN_IDENTITY" ] && [ -n "$NOTARY_PROFILE" ]
then
    echo "NOTARY_PROFILE requires SIGN_IDENTITY"
    exit 1
fi

if [ -n "$SIGN_IDENTITY" ]
then
    SIGN_IDENTITY="$SIGN_IDENTITY" $DEPLOY_DIR/sign.sh "$RELEASE_DIR/$APP_NAME.app"
elif [ "$ARCH" = "arm64" ]
then
    SIGN_IDENTITY=- $DEPLOY_DIR/sign.sh "$RELEASE_DIR/$APP_NAME.app"
fi

# submits a file to Apple and waits for the verdict, the log is printed when notarization fails
notarize() {
    xcrun notarytool submit "$1" --keychain-profile "$NOTARY_PROFILE" --wait | tee notarize.log
    if ! grep -q "status: Accepted" notarize.log
    then
        SUBMISSION_ID=$(awk '/^ *id:/ {print $2; exit}' notarize.log)
        xcrun notarytool log "$SUBMISSION_ID" --keychain-profile "$NOTARY_PROFILE"
        exit 1
    fi
}

if [ -n "$NOTARY_PROFILE" ]
then
    echo "Notarizing the app"
    ditto -c -k --keepParent "$RELEASE_DIR/$APP_NAME.app" "$TEMP_DIR/notarize.zip"
    notarize "$TEMP_DIR/notarize.zip"
    xcrun stapler staple "$RELEASE_DIR/$APP_NAME.app"
fi

# Create dmg file

# Install dmgbuild command line tool
pip3 install dmgbuild

dmgbuild -s $DEPLOY_DIR/settings.py -D app="$RELEASE_DIR/$APP_NAME.app" "$APP_NAME" "$APP_LONG_VERSION"_mac_$ARCH.dmg

if [ -n "$SIGN_IDENTITY" ]
then
    codesign --force --sign "$SIGN_IDENTITY" ${KEYCHAIN:+--keychain "$KEYCHAIN"} --timestamp "$APP_LONG_VERSION"_mac_$ARCH.dmg
fi

if [ -n "$NOTARY_PROFILE" ]
then
    echo "Notarizing the dmg"
    notarize "$APP_LONG_VERSION"_mac_$ARCH.dmg
    xcrun stapler staple "$APP_LONG_VERSION"_mac_$ARCH.dmg
fi

mv "$APP_LONG_VERSION"_mac_$ARCH.dmg $RELEASE_DIR

# Remove tmp folder
cd $DEPLOY_DIR

echo "deactivating virtual env and cleaning temp folder"

deactivate

rm -rf $TEMP_DIR
