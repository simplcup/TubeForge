# Third-party notices

TubeForge is distributed under the **GNU General Public License v3.0** (see
[`LICENSE`](LICENSE)). It bundles or links the components below. This file is the
notice that must accompany every binary release of TubeForge.

Last updated for desktop **1.0.8** and Android **1.0.1**.

---

## Download engine and media tools

| Component | Version shipped | Licence | Source |
| --- | --- | --- | --- |
| **yt-dlp** (desktop) | 2026.10.21 | Unlicense | https://github.com/yt-dlp/yt-dlp |
| **youtubedl-android** (Android, `library` + `ffmpeg` artifacts) | 0.17.4 | GPL-3.0 | https://github.com/JunkFood02/youtubedl-android |
| **yt-dlp** (Android, raw `yt-dlp` script inside the engine) | bundled with youtubedl-android 0.17.4 | Unlicense | https://github.com/yt-dlp/yt-dlp |
| **ffmpeg / ffprobe** (desktop) | `N-128718-gb2b543c079-20261109`, built with `--enable-gpl --enable-version3` | GPL-3.0 | https://ffmpeg.org/download.html — commit `b2b543c079`, build scripts at https://github.com/BtbN/FFmpeg-Builds |
| **ffmpeg / ffprobe** (Android) | Termux `ffmpeg` package, repackaged by youtubedl-android | GPL-3.0 | https://github.com/termux/termux-packages/tree/master/packages/ffmpeg |
| **CPython** (Android, embedded in `libpython.zip.so`) | 3.11 | PSF-2.0 | https://www.python.org/ |

The desktop ffmpeg build is **GPL-3.0**, not LGPL, because it enables
`--enable-gpl --enable-version3` (x264, x265, libxvid, …). The Android ffmpeg build is
likewise GPL-enabled. This is why TubeForge itself is released under the GPL-3.0:
the two cannot be combined with proprietary code.

## Desktop runtime (Python)

| Component | Version | Licence | Source |
| --- | --- | --- | --- |
| **PySide6 / Qt 6** | 6.12.0 (Essentials) | LGPL-3.0 | https://code.qt.io/cgit/pyside/pyside-setup.git/ · https://download.qt.io/official_releases/QtForPython/ |
| **mutagen** | 1.48.1 | GPL-2.0-or-later | https://github.com/quodlibet/mutagen |
| **curl_cffi** | ≥ 0.10, < 0.17 | MIT | https://github.com/lexiforest/curl_cffi |
| **certifi** | as resolved by pip | MPL-2.0 | https://github.com/certifi/python-certifi |
| **requests** | as resolved by pip | Apache-2.0 | https://github.com/psf/requests |
| **urllib3**, **idna**, **charset-normalizer** | as resolved by pip | MIT / BSD / MIT | PyPI project pages |
| **cffi** | as resolved by pip | MIT | https://github.com/python-cffi/cffi |

**Qt / PySide6 (LGPL-3.0) note.** The desktop build is a PyInstaller bundle that
carries the unmodified Qt libraries. Because the complete TubeForge source and build
scripts are published in this repository, anyone can replace the bundled Qt/PySide6
with a modified build and relink by re-running `build.ps1`. No Qt code was modified.

**Build-time only (not redistributed):** PyInstaller 6.22.3 (GPL-2.0 with a special
exception for the bootloader), Pillow, Inno Setup 6, Gradle, Android SDK/AGP, JDK 17.

## Android runtime

| Component | Version | Licence | Source |
| --- | --- | --- | --- |
| **AndroidX** (core-ktx, appcompat, recyclerview, constraintlayout, lifecycle) | 1.13.1 / 1.7.0 / 1.3.2 / 2.1.4 / 2.8.6 | Apache-2.0 | https://github.com/androidx/androidx |
| **Material Components for Android** | 1.12.0 | Apache-2.0 | https://github.com/material-components/material-components-android |
| **Kotlin standard library** | 2.0.x | Apache-2.0 | https://github.com/JetBrains/kotlin |
| **kotlinx.coroutines** | 1.8.1 | Apache-2.0 | https://github.com/Kotlin/kotlinx.coroutines |

Apache-2.0 requires that this notice and the upstream `NOTICE` text travel with the
binary. The dependency `META-INF/LICENSE` / `META-INF/NOTICE` entries are therefore
kept inside the APK (they are not stripped by the Gradle packaging rules), and the
same information is reachable in the app via **Settings → About → Open-source
licences**.

## Written offer for source

To satisfy GPL-3.0 §6, the **complete corresponding source** for every binary in this
repository is published here, at the same version tag as the release:

- TubeForge desktop: this repository, `desktop/` (plus `requirements.txt`,
  `TubeForge.spec`, `build.ps1`, `build_installer.ps1`).
- TubeForge Android: this repository, `android/` (plus Gradle files and the exact
  dependency versions listed above).
- youtubedl-android 0.17.4: https://github.com/JunkFood02/youtubedl-android (tag
  `0.17.4`), including the `libpython.zip.so` / `libffmpeg.zip.so` sources it packages.
- ffmpeg desktop build: commit `b2b543c079` of https://git.ffmpeg.org/ffmpeg.git,
  configured with the flags printed by `ffmpeg -version` (reproducible with the
  scripts at https://github.com/BtbN/FFmpeg-Builds).
- ffmpeg Android build: https://github.com/termux/termux-packages/tree/master/packages/ffmpeg.
- CPython 3.11: https://www.python.org/downloads/source/.

If a download link above ever stops working, open an issue on this repository and a
copy of the corresponding source will be provided instead.

---

*TubeForge is not affiliated with, endorsed by, or sponsored by YouTube, Google LLC,
or any of the sites it can download from. "YouTube" is a trademark of Google LLC and
is used here only to describe compatibility.*
