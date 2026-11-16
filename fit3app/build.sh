#!/usr/bin/env bash
# Builds the Fit3-App with fit3app-bt-open.patch (a debug APK, installs beside the original app).
# Needs: git, JDK 17+, the Android SDK (platform 35) in $ANDROID_HOME.
# Usage: fit3app/build.sh [out.apk]
set -euo pipefail
FIT3APP_URL="https://github.com/yuriyurin/Fit3-App"
FIT3APP_COMMIT="1ac39f0"
here="$(cd "$(dirname "$0")" && pwd)"
out="$(realpath -m "${1:-Fit3App-fit3plugin.apk}")"
work="$here/../build/fit3-app"
[ -d "$work/.git" ] || git clone --quiet "$FIT3APP_URL" "$work"
git -C "$work" checkout --quiet --force "$FIT3APP_COMMIT"
git -C "$work" apply "$here/fit3app-bt-open.patch"
echo "sdk.dir=${ANDROID_HOME:?set ANDROID_HOME}" > "$work/local.properties"
(cd "$work" && ./gradlew --no-daemon -q --max-workers=1 :app:assembleDebug :app:testDebugUnitTest --tests '*Fit3FirmwareSessionTest*' --tests '*BandFileTransportTest*')
cp "$work/app/build/outputs/apk/debug/app-debug.apk" "$out"
echo "wrote $out"
