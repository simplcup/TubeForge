<div align="center">

<img src="docs/logo.png" width="92" alt="TubeForge logo">

<h1>TubeForge</h1>

<p><b>Media Studio — save YouTube (and 1,000+ other sites) as audio or video.</b></p>

<p>Two native editions that share one design language: a <b>Windows desktop app</b> built with
PySide6, and an <b>Android app</b> built with Kotlin.</p>

<p>
  <img alt="Windows 10/11" src="https://img.shields.io/badge/Windows-10%20%2F%2011-0078D4?logo=windows&logoColor=white">
  <img alt="Android 10+" src="https://img.shields.io/badge/Android-10%2B-3DDC84?logo=android&logoColor=white">
  <img alt="Desktop 1.0.8" src="https://img.shields.io/badge/desktop-1.0.8-7C5CFF">
  <img alt="Android 1.0.1" src="https://img.shields.io/badge/android-1.0.1-22D3EE">
  <img alt="License GPL-3.0" src="https://img.shields.io/badge/license-GPL--3.0-blue">
</p>

</div>

---

## Two editions, one app

| | **Desktop** | **Android** |
| --- | --- | --- |
| Platform | Windows 10 / 11, x64 | Android 10+ (API 29), arm64-v8a |
| Version | 1.0.8 | 1.0.1 |
| UI toolkit | PySide6 6.12 (Qt 6) | Kotlin + XML layouts, Material |
| Download engine | yt-dlp + ffmpeg (bundled) | `youtubedl-android` 0.17.4 — bundles CPython 3.11, yt-dlp, ffmpeg, ffprobe |
| Distribution | Per-user Inno Setup installer, 95 MB | Sideloaded APK, 42 MB |
| Installed size | ≈ 235 MB (ffmpeg included) | ≈ 75 MB after the first-run unpack |
| Output folder | Any folder you pick (default `Downloads\TubeForge`) | `Download/TubeForge` (shared storage, MediaStore) |
| Background work | In-app queue, window stays open | Foreground service + progress notification |

Same palettes, same sections (Download / Queue / History / Settings), same formats,
same one-at-a-time download model. The desktop build additionally has browser-cookie
import, drag-and-drop and ffmpeg auto-detection; the Android build adds a share-sheet
target and survives leaving the app.

## Screenshots

### Desktop (Windows)

| | |
|:--:|:--:|
| ![Download page](docs/desktop-download.png) | ![Queue page](docs/desktop-queue.png) |
| <sub><b>Download</b> — fetch, preview, choose a format</sub> | <sub><b>Queue</b> — progress, speed and ETA</sub> |
| ![Settings page](docs/desktop-settings.png) | ![Deep Ocean theme](docs/desktop-theme.png) |
| <sub><b>Settings</b> — output, downloads, engine</sub> | <sub><b>Themes</b> — Deep Ocean applied live</sub> |

### Android

| | |
|:--:|:--:|
| <img src="docs/mobile-download.png" width="300" alt="Android download page"> | <img src="docs/mobile-settings.png" width="300" alt="Android settings page"> |
| <sub><b>Download</b> — same format chips, touch layout</sub> | <sub><b>Settings</b> — themes, proxy, embedding</sub> |

Both editions share the eight palettes and the four sections; the Android build
uses a bottom navigation bar and full-width cards.

## Download

Builds are attached to the repository's **Releases** page:

| Edition | File | Size | SHA-256 |
| --- | --- | --- | --- |
| Windows | `TubeForge-Setup-1.0.8.exe` | 95 MB | `8E75C56D9B010052E57AEAF58446CF64B2CDD149260BFB1AAC52B07CD9F28D71` |
| Android | `TubeForge-Android-1.0.1.apk` | 42 MB | `AD07196756CF0897F75406B0BCCC9DF94DE3E137E540F2D8537BA9372D6DC1C5` |

Verify an APK before installing:

```powershell
Get-FileHash .\TubeForge-Android-1.0.1.apk -Algorithm SHA256
```

Neither build has a paid code-signing certificate, so Windows SmartScreen and Android
Play Protect may warn that the publisher is unknown. That is expected for self-built
software; both builds are safe to allow.

## Quick start

1. Paste a link — or on Android, share one into TubeForge from another app.
2. Press **Fetch** to preview the title, thumbnail, channel and duration.
3. Pick an audio or video format, optionally cap the resolution.
4. Press **Download** and watch it on the **Queue** page. Finished files appear in **History**.

## Formats

**Audio**

| Format | Details |
| --- | --- |
| MP3 | 320 kbps, plays everywhere |
| M4A | AAC audio, Apple-friendly |
| OPUS | keeps the original opus stream (no re-encode) |
| FLAC | lossless |
| WAV | uncompressed PCM |

**Video**

| Format | Details |
| --- | --- |
| MP4 | H.264 + AAC, maximum compatibility |
| WEBM | VP9 + Opus, smaller files |
| MKV | best available codecs, flexible container |

Video quality: **Best available**, then 2160p, 1440p, 1080p, 720p, 480p or 360p
(Android lists the heights the source actually offers, up to 2160p).

## Features

**Both editions**

- Fetched metadata preview — title, uploader, duration, thumbnail, source chip.
- Sequential queue with live percentage, speed and ETA; cancel queued or running jobs.
- Persistent **History** with an *Open* action for finished files.
- **Eight themes**, applied instantly and remembered: Midnight Violet, Aurora,
  Sunset Heat, Deep Ocean, Evergreen, Crimson, Graphite (mono), Sepia (mono).
- **Optional proxy** for region-locked media — `http://`, `https://` or `socks5://`,
  with optional user/password.
- **Cover art + metadata embedding** (toggleable).
- Bundled **ffmpeg** — no separate install, no PATH setup.
- Errors are cleaned up and shown inline: ANSI noise stripped, tracebacks trimmed to
  the useful lines.

**Desktop only**

- Frameless window with accent gradients, animated progress and toasts.
- **Retry** failed jobs; thumbnail cache; open file or containing folder from History.
- Browser cookies for age-restricted / private / members-only media — Chrome, Edge,
  Firefox, Brave, Opera, Vivaldi, or a Netscape `cookies.txt`. Chromium browsers are
  briefly closed, their cookie DB snapshotted, then reopened with your tabs.
- **Automatic bot-check handling** — retries with yt-dlp's browser impersonation
  (`curl_cffi`) when a site answers with a Cloudflare challenge.
- **Force IPv4** on by default — fixes IPv6 CDN connection stalls on some networks.
- ffmpeg auto-detection with one-click `winget` install or a manual path picker.
- Drag a link anywhere onto the window to start; custom output folder and file-name
  template (`%(title)s.%(ext)s`).

**Android only**

- **Share-sheet target** — share a YouTube link from any app and TubeForge prefetches it.
- **Foreground service** with a live progress notification, so downloads continue
  while the app is backgrounded or the screen is off.
- **Scoped-storage friendly output** — files land in `Download/TubeForge` through
  MediaStore and show up in the gallery / file manager. No storage permission
  required on Android 10+.
- **Plain-language error hints** mapped from engine output — private video, region
  block, bot check, HTTP 403, out of storage, connection timeout and so on.
- One-tap **Update yt-dlp** in Settings (fixes most engine breakages after site changes).
- **Licences built in** — GPL-3.0 plus every bundled component's notice ships inside
  the APK and is readable from **Settings → About → Open-source licences**.

## Desktop (Windows)

### Install

Run `TubeForge-Setup-1.0.8.exe`. The installer:

- installs for the current user (**no administrator prompt**) into
  `%LOCALAPPDATA%\Programs\TubeForge`,
- bundles ffmpeg and ffprobe, so nothing else is needed,
- adds Start Menu and optional Desktop shortcuts,
- registers in **Settings → Apps**, where it can be uninstalled.

Uninstalling removes program files and shortcuts but keeps settings, history and
your downloaded media.

### Files and settings

| What | Where |
| --- | --- |
| Program | `%LOCALAPPDATA%\Programs\TubeForge` |
| Settings / history | `%APPDATA%\TubeForge` |
| Default downloads | `%USERPROFILE%\Downloads\TubeForge` |

### Build from source

```powershell
cd desktop
python -m pip install -r requirements.txt
python run.py
```

Python 3.10+ and Windows. Requires the 64-bit CPython build.

```powershell
.\build.ps1            # -> dist\TubeForge.exe  (PyInstaller)
.\build_installer.ps1  # -> dist\TubeForge-Setup-1.0.8.exe  (Inno Setup 6)
```

`build_installer.ps1` needs [Inno Setup 6](https://jrsoftware.org/isinfo.php) and the
ffmpeg binaries in `vendor\ffmpeg\bin`. **The 185 MB of ffmpeg binaries are not
committed.** Download a Windows x64 *GPL shared* build from
[BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds/releases) (the release used
`N-128718-gb2b543c079`, `--enable-gpl --enable-version3`) and drop its `bin\` and
`LICENSE.txt` into `desktop\vendor\ffmpeg\`. The icon can be regenerated with
`python tools\make_icon.py`.

Diagnostics in a packaged build (JSON written to `%TEMP%`):

```powershell
.\dist\TubeForge.exe --check          # Qt / TLS / SVG / ffmpeg checks
.\dist\TubeForge.exe --download-test  # real MP3 download through the engine
.\dist\TubeForge.exe --ui-test        # window / themes / proxy-card smoke test
```

## Android

### Requirements

- Android **10 or newer** (API 29).
- **arm64-v8a** device (the norm for phones since around 2017). The APK is not built
  for x86 emulators or 32-bit devices.
- ≈ 80 MB free storage for the app plus whatever you download.

### Install

1. Copy `TubeForge-Android-1.0.1.apk` to the phone.
2. Allow "install unknown apps" for the app that opens it, then install.
3. On first launch the engine unpacks CPython and ffmpeg and installs yt-dlp — a few
   seconds of background work, once per install.
4. Grant the notification permission when asked (Android 13+); it powers the
   download progress notification.

Over USB with `adb`:

```bash
adb install -r TubeForge-Android-1.0.1.apk
```

### Storage

Finished files are published to **`Download/TubeForge`** through MediaStore, so they
are visible in the gallery, file managers and USB transfers without any storage
permission. Downloads are staged in the app cache and removed once published.

### Build from source

Requirements: **JDK 17**, Android SDK with platform/build-tools 35. The Gradle 8.11.1
wrapper is included. Create `local.properties` with `sdk.dir=…` or set `ANDROID_HOME`.

```bash
cd mobile
./gradlew assembleRelease        # Windows: gradlew.bat assembleRelease
# -> app/build/outputs/apk/release/app-release.apk
```

Notes:

- `abiFilters = arm64-v8a`, `minSdk 29`, `targetSdk 35`.
- The release variant is signed with the local debug keystore so it sideloads without
  extra setup. Replace `signingConfig` in `app/build.gradle.kts` with your own keystore
  before publishing to a store.
- `extractNativeLibs=true` and `jniLibs.useLegacyPackaging=true` are **required**:
  the engine loads `libpython.zip.so` / `libffmpeg.zip.so` from `nativeLibraryDir`.

### Not ported to Android

Browser-cookie import, the ffmpeg path picker, drag-and-drop, custom title bar /
taskbar effects and the separate Windows installer are desktop-only by design.
Playlists behave the same on both editions: only the first item is used.

## Repository layout

This README works for a single repository holding both editions:

```
README.md               this file
RELEASE-NOTES.md        text for the GitHub Release body
PUBLISHING.md           step-by-step push + release checklist
LICENSE                 GPL-3.0 full text
THIRD-PARTY-NOTICES.md  every bundled component, version, licence, source
PRIVACY.md              what the app talks to and stores
.gitignore              keeps keystores, local paths and build output out of git
.gitattributes          line endings (gradlew stays LF)
docs/                   screenshots used above
desktop/                PySide6 app (run.py, app/, installer/, tools/)
mobile/                 Kotlin app (gradlew, app/src, tools/)
releases/               the two installers to attach to a GitHub Release (not committed)
```

If you keep two repositories instead, copy this README, `LICENSE`,
`THIRD-PARTY-NOTICES.md`, `PRIVACY.md` and `docs/` into each repo root, and link the
other repository from the header.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| *"Sign in to confirm you're not a bot"* | Desktop retries with impersonation automatically; if it still fails, set **Settings → Downloads → Browser cookies** to the browser you're signed in to. On Android, press **Update yt-dlp** first. |
| *"Video not available in your country"* | Set a proxy in **Settings → Proxy**. |
| Download fails out of nowhere | Site extractors change constantly — update yt-dlp (Android: **Settings → Update**; desktop: reinstall the latest build). |
| Desktop says ffmpeg is missing | **Settings → Tools → Install with winget**, or **Locate** `ffmpeg.exe`. |
| Android downloads stall in the background | Allow notifications for TubeForge so the progress notification stays visible — some OEM builds are aggressive about stopping services whose notification is hidden. Also exclude TubeForge from battery optimisation. |
| Files "not showing up" on Android | They are in `Download/TubeForge`. Some gallery apps need a refresh; a file manager will see them immediately. |

## Licence

TubeForge is released under the **GNU General Public License v3.0** — see
[`LICENSE`](LICENSE). That is not a preference: the Android build links
[youtubedl-android](https://github.com/JunkFood02/youtubedl-android) (GPL-3.0) and both
builds ship a **GPL-enabled ffmpeg**, so the combined work has to be GPL-3.0.

In short, you may use, study, share and modify it; if you distribute a build, you must
publish the source under the same licence.

### Third-party components

The full list, with versions, licences and upstream links, is in
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md). The highlights:

| Component | Licence |
| --- | --- |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Unlicense |
| [youtubedl-android](https://github.com/JunkFood02/youtubedl-android) (Android engine, bundles CPython + yt-dlp + ffmpeg) | GPL-3.0 |
| [ffmpeg](https://ffmpeg.org/) — desktop `N-128718-gb2b543c079`, `--enable-gpl --enable-version3`; Android Termux build | GPL-3.0 |
| [PySide6 / Qt 6](https://doc.qt.io/qtforpython-6/) (desktop UI) | LGPL-3.0 |
| [mutagen](https://mutagen.readthedocs.io/) (tags, cover art) | GPL-2.0-or-later |
| [curl_cffi](https://github.com/lexiforest/curl_cffi) (browser impersonation) | MIT |
| [certifi](https://github.com/certifi/python-certifi) | MPL-2.0 |
| AndroidX + Material Components + Kotlin coroutines | Apache-2.0 |

On Android the same texts ship inside the APK
(`assets/licences/NOTICES.txt`) and are readable from **Settings → About →
Open-source licences**. Qt/PySide6 is bundled unmodified; the published source and
build scripts let anyone swap in a patched Qt and relink.

Source for every binary is published in this repository at the release tag, and the
upstream commits for ffmpeg/yt-dlp/youtubedl-android are pinned in
[`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md) — that is the GPL-3.0 §6 written
offer.

## Privacy

No accounts, no analytics, no telemetry, no ads, no author-operated server. Requests go
only to the site you download from (plus GitHub for **Update yt-dlp**), and browser
cookies stay on your machine. Details: [`PRIVACY.md`](PRIVACY.md).

## Legal and fair use

**TubeForge is not affiliated with, endorsed by, or sponsored by YouTube, Google LLC,
or any of the sites it can download from.** "YouTube" is a trademark of Google LLC and
is used here only to describe compatibility.

The tool is a general-purpose downloader, like a web browser's "save as". What you do
with it is your responsibility:

- Downloading a video does not grant you a licence to it. Copyright stays with the
  rightsholder. Keep personal copies only where your local law allows it, and never
  redistribute, re-upload or monetise someone else's work.
- Downloading may violate a site's **Terms of Service** even where copyright law
  permits it. That is a contract question, not a copyright one, and it is between you
  and the site.
- Do not use it to bypass paywalls, DRM, or access controls. The app has no DRM
  circumvention of any kind, and it cannot download paid or protected streams.
- If you host a build, respond to valid DMCA/notice-and-takedown requests for content
  *you* host. TubeForge hosts no media and contains no catalogue.

If you plan to distribute this in a store (Google Play, Microsoft Store) or
commercially, get legal advice first: store policies on downloader apps are stricter
than the GPL, and the app's GPL-3.0 engine rules out proprietary redistribution.

