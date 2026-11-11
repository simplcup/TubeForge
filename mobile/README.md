# TubeForge for Android

Native Android edition of [TubeForge](../README.md) — same palettes, same four
sections, rebuilt as a touch UI around a bundled yt-dlp + ffmpeg engine.

| | |
| --- | --- |
| Package | `com.tubeforge.mobile` |
| Version | 1.0.1 (versionCode 2) |
| Min Android | 10 (API 29) |
| Target / compile SDK | 35 |
| ABI | `arm64-v8a` |
| Engine | [`youtubedl-android`](https://github.com/JunkFood02/youtubedl-android) 0.17.4 (`library` + `ffmpeg`) — bundles CPython 3.11, yt-dlp and ffmpeg |
| Output | `Download/TubeForge` (MediaStore, no storage permission needed) |
| Licence | GPL-3.0 — see [`../LICENSE`](../LICENSE) and [`../THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md) |

First launch unpacks CPython/yt-dlp/ffmpeg from `libpython.zip.so` /
`libffmpeg.zip.so` into the app's native library directory. A few seconds, on a
background thread, once per install.

## Build

Requires **JDK 17** and an Android SDK with platform + build-tools 35.

```bash
export JAVA_HOME=/path/to/jdk-17
export ANDROID_HOME=/path/to/android-sdk      # or write local.properties

cd mobile
./gradlew assembleRelease                     # Windows: gradlew.bat assembleRelease
# -> app/build/outputs/apk/release/app-release.apk
```

The release variant is signed with the local debug keystore so it sideloads without
extra setup. Replace `signingConfig` in `app/build.gradle.kts` with your own keystore
for anything beyond personal use.

`extractNativeLibs=true` and `jniLibs.useLegacyPackaging=true` are **required** — the
engine loads `libpython.zip.so` and `libffmpeg.zip.so` from `nativeLibraryDir`.

## Layout

```
app/src/main/java/com/tubeforge/mobile/
  MainActivity.kt     pages, chips, theming, fetch/download, licence dialog
  QueueManager.kt     job list, worker loop, yt-dlp request building
  Engine.kt           youtubedl-android wrapper + friendly error messages
  DownloadService.kt  foreground service + progress notification
  MediaSaver.kt       publish finished file into MediaStore Downloads
  Palette.kt          the 8 shared palettes
  ThemeUi.kt          tag-based runtime theming (bg/card/title/accentText/…)
  Model.kt            Job, HistoryEntry, MediaInfo, Fmt
  Store.kt            atomic JSON persistence
  Format.kt           byte/speed/eta formatting, MIME mapping
  JobAdapter.kt, HistoryAdapter.kt
app/src/main/assets/licences/NOTICES.txt   GPL-3.0 + third-party notices shown in-app
app/src/main/res/layout/                   activity_main, page_*, item_*
tools/make_icons.py                         launcher icons from ../desktop/assets/logo.png
tools/strip_bom.py                          removes UTF-8 BOMs that break aapt2
```

## Not ported from desktop

Browser-cookie import, the ffmpeg path picker, drag-and-drop, custom title bar and the
Windows installer. Playlists behave the same on both editions: only the first item is
used.
