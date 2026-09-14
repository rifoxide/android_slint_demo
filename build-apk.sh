#!/data/data/com.termux/files/usr/bin/sh
set -eu
ROOT="$(cd "$(dirname "$0")" && pwd)"
PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
export JAVA_HOME="$PREFIX/lib/jvm/java-17-openjdk"
export ANDROID_JAR="$ROOT/tools/android.jar"
export ANDROID_D8_JAR="$ROOT/tools/r8.jar"

cargo build

rm -rf apk-stage
mkdir -p apk-stage/lib/arm64-v8a
cp target/debug/libslintdemo.so apk-stage/lib/arm64-v8a/
cp "$PREFIX/lib/libc++_shared.so" apk-stage/lib/arm64-v8a/

UNSIGNED=slint-demo-unsigned.apk
aapt package -f -M AndroidManifest.xml -I /system/framework/framework-res.apk -F "$UNSIGNED"
(
	cd apk-stage
	aapt add "../$UNSIGNED" lib/arm64-v8a/libslintdemo.so
	aapt add "../$UNSIGNED" lib/arm64-v8a/libc++_shared.so
)

python3 sign_apk_v2.py "$UNSIGNED" slint-demo.apk "$ROOT/keystore/key.pem" "$ROOT/keystore/cert.der" "$ROOT/keystore/pub.der"
rm -rf "$UNSIGNED" apk-stage
md5sum slint-demo.apk
