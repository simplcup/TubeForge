# TubeForge — Media Studio

A native Windows desktop app for saving YouTube (and 1,000+ other sites) media as
**MP3, FLAC, WAV, OPUS, M4A, MP4, WEBM or MKV**, with a modern dark UI, live queue,
progress, history and embedded cover art.

Built with PySide6 + yt-dlp + ffmpeg. Ships as a self-contained Windows installer.

---

## Install

Run **`TubeForge-Setup-1.0.8.exe`**. The installer:

- installs TubeForge for the current user (no administrator prompt),
- bundles **ffmpeg and ffprobe**, so no extra tools are needed,
- adds Start Menu and optional Desktop shortcuts,
- registers TubeForge in **Settings → Apps**, where it can be uninstalled.

Uninstalling removes the program files and shortcuts but keeps your settings,
history and downloaded media. You can also run the uninstaller from the
TubeForge folder in the Start Menu.

## Quick start

1. Launch **TubeForge** from the Start Menu or Desktop shortcut.
2. Paste a link (Ctrl+V), optionally press **Fetch** to preview it.
3. Pick a format, choose a video quality, press **Download**.
4. Watch it on the **Queue** page; finished files appear in **History**.

Downloads default to `C:\Users\<you>\Downloads\TubeForge`. Change it on the
Download page or in Settings.

## Formats

| Audio | Details |
| --- | --- |
| MP3 | 320 kbps, plays everywhere |
| FLAC | lossless |
| WAV | uncompressed PCM |
| OPUS | keeps the original opus stream (no re-encode) |
| M4A | AAC audio, Apple-friendly |

| Video | Details |
| --- | --- |
| MP4 | H.264 + AAC, maximum compatibility, fast-start |
| WEBM | VP9 + Opus, smaller files |
| MKV | best available codecs, flexible container |

Video quality: Best available, 2160p, 1440p, 1080p, 720p, 480p or 360p.

## Features

- Fancy frameless UI with accent gradients, animated progress and toasts.
- **Eight themes** — six colourful palettes (Midnight Violet, Aurora, Sunset Heat,
  Deep Ocean, Evergreen, Crimson) and two monochrome ones (Graphite, Sepia).
  Switch them in Settings → Appearance; the whole window recolours instantly.
- Metadata/thumbnail preview before downloading.
- Background queue with one-at-a-time downloads, cancel, retry and live speed/ETA.
- Persistent history with open-file / open-folder actions and thumbnail cache.
- Cover art + metadata embedding (toggleable).
- **Optional proxy** for region-blocked media — HTTP, HTTPS or SOCKS5.
- **Automatic bot-check handling** — retries with yt-dlp's browser impersonation
  (`curl_cffi`) when a site serves a Cloudflare challenge.
- Browser-cookie support for age-restricted/private media (Chrome, Edge, Firefox,
  Brave, Opera, Vivaldi).
- **Force IPv4** enabled by default — fixes the "connection reset" stalls this
  network exhibits on YouTube's IPv6 CDN.
- ffmpeg auto-detection with one-click `winget` install or manual locate.
- Drag a link anywhere onto the window to start.

## Themes

Open **Settings → Appearance** and pick a palette. The change is applied live —
no restart — and the choice is remembered. Every palette is generated from a
single colour set, so icon tints, progress bars, chips, the title bar and toasts
all follow the theme. Graphite and Sepia are deliberately monochrome for a
quieter look.

## Region-locked media (proxy)

Some tracks are blocked in your country (`This video is not available from your
location`). TubeForge can route the download through an optional **proxy** so the
site sees an IP address in a permitted region.

Open **Settings → Proxy** and enter the proxy address. Supported forms:

| Scheme | Example |
| --- | --- |
| HTTP / HTTPS | `http://127.0.0.1:8080` |
| SOCKS5 | `socks5://127.0.0.1:1080` |
| With authentication | `http://user:password@127.0.0.1:8080` |

Leave the field blank to connect directly. The proxy is used by the yt-dlp engine
for both metadata fetching and downloading.

> **What goes in this field?** The address of a proxy server — **not** a YouTube,
> SoundCloud or other media link. Media links belong on the **Download** page.

Typical setups:

- A local VPN/proxy client (Clash, V2Ray, Shadowsocks) usually exposes an HTTP
  port such as `7890` or a SOCKS port such as `1080`.
- A remote proxy or VPS with an HTTP/SOCKS endpoint, e.g.
  `http://203.0.113.10:3128`.
- A browser proxy extension's address, if it exposes a local port.

A proxy is **not** a download accelerator. A slow or distant proxy can make
downloads slower; use one close to you and only when a title is blocked.

## Sites with bot checks

Some sites answer with a Cloudflare / anti-bot challenge (HTTP 403). yt-dlp's
solution is browser impersonation, which needs the optional `curl_cffi` package
(bundled with TubeForge). When the first attempt fails with a bot-check error,
TubeForge automatically retries with:

```
--extractor-args "generic:impersonate"
```

If a site still refuses, enable **Settings → Downloads → Browser cookies** and
sign in to that browser first; some sites require a real session.

Chromium-family browsers (Chrome, Edge, Brave, Opera and Vivaldi) lock their
cookie database while running, so Windows will not let another program read it.
When that happens TubeForge asks to **close the browser for a moment**, copies
the cookies to a temporary file, and reopens the browser with your tabs. The
snapshot is reused for about 30 minutes; Firefox cookies work while Firefox is
open. You can also point TubeForge at a Netscape `cookies.txt` file instead.

## ffmpeg

Merging and conversion need **ffmpeg**. TubeForge finds it automatically from
PATH, a bundled/app folder, or winget packages. If it is missing:

**Settings → Tools → Install with winget** (or **Locate** to point at `ffmpeg.exe`).

## Tips

- **"Sign in to confirm you're not a bot"** → TubeForge already retries with
  browser impersonation. If it still fails, open Settings → Downloads → Browser
  cookies, pick the browser you're signed in to, then retry.
- **"Not available in your country"** → set a proxy in Settings → Proxy.
- The source chip shows the site you pasted (e.g. `YUMMYNIME`), not the host
  yt-dlp redirected to.
- Playlists are not expanded yet; the first item is used.
- Live streams only capture what plays while connected.
- Only download content you have the right to save.

## Run from source

```powershell
python -m pip install -r requirements.txt
python run.py
```

## Build the executable

```powershell
.\build.ps1
# -> dist\TubeForge.exe
```

The icon can be regenerated with `python tools\make_icon.py`.

## Build the installer

```powershell
.\build_installer.ps1
# -> dist\TubeForge-Setup-1.0.8.exe
```

`build_installer.ps1` uses [Inno Setup 6](https://jrsoftware.org/isinfo.php) and
bundles the ffmpeg files from `vendor\ffmpeg\bin`. Inno Setup's generated
`unins000.exe` is the uninstaller. The installer is per-user and does not
require administrator rights.

> **Python 3.10.0 builders:** `TubeForge.spec` applies a build-time fix for a
> CPython `dis` bug that crashes PyInstaller's analysis (fixed upstream in
> 3.10.1). See `build/cpython_dis_fix.py`; newer interpreters can ignore it.

Packaged-build diagnostics (windowed exe writes JSON to `%TEMP%`):

```powershell
.\dist\TubeForge.exe --check          # Qt/TLS/SVG/ffmpeg checks
.\dist\TubeForge.exe --download-test  # real MP3 download through the engine
.\dist\TubeForge.exe --ui-test        # window/themes/proxy-card smoke test + screenshots
Get-Content $env:TEMP\TubeForge-check.json
```

## Layout

```
run.py                  entry point
app/core.py             settings, history, ffmpeg finder, yt-dlp queue
app/pages.py            Download / Queue / History / Settings pages
app/widgets.py          custom-painted UI components
app/window.py           frameless main window
app/theme.py            palette + stylesheet
app/diagnostics.py      packaged-build checks
assets/                 icon + logo
installer/TubeForge.iss Inno Setup installer + uninstaller script
vendor/ffmpeg/          bundled ffmpeg/ffprobe used by the installer
tools/                  icon generator, tests, screenshots, frozen-build capture
TubeForge.spec          PyInstaller build
```

## Credits and licence

- Download engine: [yt-dlp](https://github.com/yt-dlp/yt-dlp) by the yt-dlp
  contributors, released under the [Unlicense](https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE).
- Browser impersonation is provided by
  [curl_cffi](https://github.com/lexiforest/curl_cffi).
- Media conversion uses [ffmpeg](https://ffmpeg.org/).
- The interface is built with [PySide6](https://doc.qt.io/qtforpython-6/).
