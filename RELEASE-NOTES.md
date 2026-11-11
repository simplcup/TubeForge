# TubeForge 1.0.8 (desktop) · 1.0.1 (Android)

Two native editions of the same media downloader: a **Windows desktop app** built with
PySide6, and an **Android app** built with Kotlin. Both save YouTube (and 1,000+ other
sites) as MP3, M4A, OPUS, FLAC, WAV, MP4, WEBM or MKV.

## Files

| Asset | For | Size | SHA-256 |
| --- | --- | --- | --- |
| `TubeForge-Setup-1.0.8.exe` | Windows 10/11 x64 | 94.8 MB | `8E75C56D9B010052E57AEAF58446CF64B2CDD149260BFB1AAC52B07CD9F28D71` |
| `TubeForge-Android-1.0.1.apk` | Android 10+, arm64-v8a | 42.4 MB | `AD07196756CF0897F75406B0BCCC9DF94DE3E137E540F2D8537BA9372D6DC1C5` |
| `SHA256SUMS.txt` | both | 200 B | — |

## Desktop 1.0.8

Per-user installer, no administrator prompt, ffmpeg and ffprobe bundled.
Eight themes, download queue with progress/speed/ETA, history, browser-cookie import
(Chrome, Edge, Firefox, Brave, Opera, Vivaldi, `cookies.txt`), automatic bot-check
handling via browser impersonation, Force IPv4 by default, drag-and-drop links.

## Android 1.0.1

First public build. Foreground service so downloads survive backgrounding, share-sheet
target, MediaStore output in `Download/TubeForge` (no storage permission), one-tap
**Update yt-dlp**, licences built in under **Settings → About**.
arm64-v8a only — it will not run on x86 emulators or 32-bit devices.

## Install

- **Windows:** run the setup, allow the SmartScreen prompt (the build is not
  code-signed), launch from the Start Menu.
- **Android:** copy the APK to the phone, allow "install unknown apps", install.
  First launch unpacks the engine (~10 s, once), then grant notifications.

## Licence and source

TubeForge is **free software under the GNU GPL-3.0** (`LICENSE`). The complete
corresponding source for both editions is published in this repository at this tag;
every bundled component, its version and its upstream source is listed in
`THIRD-PARTY-NOTICES.md` (yt-dlp — Unlicense; youtubedl-android, ffmpeg — GPL-3.0;
PySide6/Qt — LGPL-3.0; AndroidX/Material — Apache-2.0).

No telemetry, no accounts, no ads — see `PRIVACY.md`.

**Not affiliated with, endorsed by, or sponsored by YouTube, Google LLC or any site it
can download from.** "YouTube" is a trademark of Google LLC, used only to describe
compatibility. Downloading does not give you a licence to the media; respect copyright
and each site's terms of service.
