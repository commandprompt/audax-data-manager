#!/bin/bash

# Signs an app bundle inside-out: Mach-O files first, then nested bundles, then the app itself.
# Usage: SIGN_IDENTITY=<identity> sign.sh <path-to.app>
#   SIGN_IDENTITY "-" signs ad-hoc (no hardened runtime), anything else is a signing identity
#   KEYCHAIN       optional keychain that holds the identity

set -e

APP="$1"
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

if [ -z "$APP" ] || [ -z "$SIGN_IDENTITY" ]
then
    echo "Usage: SIGN_IDENTITY=<identity> $0 <app>"
    exit 1
fi

OPTS=(--force --sign "$SIGN_IDENTITY")
if [ "$SIGN_IDENTITY" != "-" ]
then
    OPTS+=(--options runtime --timestamp --entitlements "$SCRIPT_DIR/entitlements.plist")
fi
if [ -n "$KEYCHAIN" ]
then
    OPTS+=(--keychain "$KEYCHAIN")
fi

echo "Signing Mach-O files"
find "$APP" -type f ! -path "*/Versions/Current/*" | while read -r f
do
    lipo -archs "$f" >/dev/null 2>&1 || continue
    codesign "${OPTS[@]}" "$f"
done

echo "Signing nested bundles"
# deepest first, so a bundle is signed after everything inside it
find "$APP" -mindepth 1 \( -name "*.app" -o -name "*.framework" -o -name "*.xpc" \) -type d ! -path "*/Versions/Current/*" |
    awk '{ print gsub("/", "/") " " $0 }' | sort -rn | cut -d' ' -f2- | while read -r b
do
    codesign "${OPTS[@]}" "$b"
done

echo "Signing $APP"
codesign "${OPTS[@]}" "$APP"

codesign --verify --deep --strict "$APP"
echo "Signature verified"
