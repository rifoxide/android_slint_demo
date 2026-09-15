# android_slint_demo

A minimal [Slint](https://slint.dev) demo app for Android — compiled, packaged
and signed **entirely on-device** from [Termux](https://termux.dev). No Android
SDK, no NDK, no Android Studio, no host machine.

Tested on the [Termux app from F-Droid](https://f-droid.org/packages/com.termux/)
on an arm64 device running Android; other Termux distribution channels
(e.g. GitHub builds) should work the same.

The demo is a simple counter (label, big number, Tap / Reset buttons) defined in
`ui/app.slint`, running as a native shared library launched through
`android.app.NativeActivity`.

## How it works

| Piece | Trick |
| --- | --- |
| Cross-compilation | None needed — Termux's Rust targets `aarch64-linux-android` natively, so the `cdylib` is a real Android library |
| Renderer | `slint` with `backend-android-activity-06` (skia GPU renderer, pulled in via the [rust-skia](https://github.com/rust-skia/skia-safe) prebuilt binary cache — no local skia build) |
| APK assembly | `aapt` packages the manifest using the device's own `/system/framework/framework-res.apk` as the framework resource package |
| C++ standard library | The NDK's `libc++_static`/`libc++abi` don't exist in Termux, so `stublibs/` contains linker scripts redirecting them to Termux's `libc++_shared.so`, which is shipped inside the APK |
| Slint's Java IME helper | `slint` compiles a small Java helper class at build time; `javac` comes from Termux's `openjdk-17`, and `d8` runs from the `r8.jar` in `tools/` (wired up via `ANDROID_JAR` / `ANDROID_D8_JAR` / `JAVA_HOME`) |
| Signing | `sign_apk_v2.py` — a minimal APK Signature Scheme v2 signer (pure Python + `openssl` for the RSA operation) implementing the AOSP digest rules, including the canonicalized EOCD central-directory offset |

## One-time setup

```sh
pkg install -y rust aapt openjdk-17 openssl-tool

mkdir -p tools keystore
curl -L -o tools/android.jar \
  https://raw.githubusercontent.com/Sable/android-platforms/master/android-30/android.jar
curl -L -o tools/r8.jar \
  https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.5.35/r8-8.5.35.jar

openssl req -x509 -newkey rsa:2048 -keyout keystore/key.pem -out keystore/cert.pem \
  -days 9131 -nodes -subj "/CN=Slint Demo/O=Slint Demo/C=US"
openssl x509 -in keystore/cert.pem -outform DER -out keystore/cert.der
openssl rsa -in keystore/key.pem -pubout -outform DER -out keystore/pub.der
```

`tools/` and `keystore/` are git-ignored. Keep `keystore/key.pem` — Android
only installs updates signed with the same key.

## Build and install

```sh
./build-apk.sh        # cargo build -> aapt package -> v2-sign -> slint-demo.apk
```

Install the resulting APK by opening it with the system installer:

```sh
termux-open --content-type application/vnd.android.package-archive slint-demo.apk
```

Allow "Install unknown apps" for Termux if prompted. First build takes a few
minutes on-device; subsequent builds are incremental.

## Layout

```
├── ui/app.slint          # the demo UI (counter)
├── src/lib.rs            # android_main entry point
├── AndroidManifest.xml   # NativeActivity manifest (org.slint.demo)
├── build.rs              # compiles app.slint via slint-build
├── build-apk.sh          # full build/package/sign pipeline
├── sign_apk_v2.py        # minimal APK v2 signer
├── stublibs/             # libc++ linker-script redirects
├── .cargo/config.toml    # adds stublibs to the link line
├── tools/                # (ignored) android.jar, r8.jar
└── keystore/             # (ignored) signing key and certificate
```

## Notes

- The femtovg renderer is not supported by Slint's Android backend; skia is
  used instead (still GPU-accelerated via OpenGL ES).
- `.cargo/config.toml` contains an absolute path to `stublibs/`; update it if
  you move the checkout.
- Demo code in this repository: do what you like with it. Slint itself is
  licensed under GPL-3.0-only OR Royalty-free / Commercial licenses — see
  [slint.dev](https://slint.dev/licensing).
