# Privacy

TubeForge has no accounts, no analytics, no telemetry, no crash reporting and no ads.
Nothing is sent to the author of this project, and there is no server operated by it.

## What leaves your device

Only the requests needed to download the media you asked for:

- the page and media URLs you paste or share into the app, requested from the site
  itself and its CDN through **yt-dlp**;
- if you configure a proxy in Settings, those requests go through that proxy instead;
- on Android, **Settings → Update yt-dlp** contacts GitHub
  (`api.github.com` / `github.com`) to fetch the current yt-dlp release;
- on desktop, **Settings → Tools → Install with winget** runs `winget`, which contacts
  Microsoft's package repository.

No usage data, download titles, URLs or identifiers are transmitted anywhere else.

## What is stored locally

| Desktop (`%APPDATA%\TubeForge`) | Android |
| --- | --- |
| `settings.json` — output folder, format, theme, proxy, cookie browser | `SharedPreferences` — same settings, stored in the app's private data directory |
| `history.json` — title, URL, format and path of finished downloads | in-memory session history |
| `cache/` — cover-art thumbnails | `cache/` — temporary download staging |

Downloaded files themselves are written to the folder you choose (desktop) or
`Download/TubeForge` (Android). Deleting a file in History only removes the entry, never
the media.

## Browser cookies (desktop only)

If you enable **Settings → Downloads → Browser cookies**, TubeForge copies the cookie
database of the selected browser to a temporary file and reads it locally. Cookies are
passed to yt-dlp as a temporary file so that age-restricted or members-only media you
already have access to can be fetched. They are never uploaded, never logged, never
stored in `settings.json` (only the browser *name* is), and the temporary copy is
deleted when the job finishes.

## Children / sensitive data

The app collects nothing, so there is nothing to request, export or delete. Removing
the app (and the `%APPDATA%\TubeForge` folder on desktop, or the app's data on Android)
removes everything the app stored.

## Contact

Open an issue on this repository for any privacy question.
