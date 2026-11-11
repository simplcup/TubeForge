# How to publish this on GitHub

Everything in this folder is ready. Nothing here needs editing before the first push
except the repository URL placeholders in `README.md` if you add any.

## 1. Create the repository

On GitHub: **New repository** → name `TubeForge` → **Public** → do *not* add a README,
licence or `.gitignore` (they are already here) → Create.

## 2. Push this folder

```powershell
cd "C:\Users\atom4\TubeForge - what to post on GitHub"
git init
git add .
git status            # sanity check: no local.properties, no *.exe/*.apk, no build/
git commit -m "TubeForge 1.0.8 desktop + 1.0.1 Android"
git branch -M main
git remote add origin https://github.com/<your-user>/TubeForge.git
git push -u origin main
```

`releases/` is git-ignored on purpose — those two binaries go to the Releases page
instead (they are too large to commit).

## 3. Tag the release

```powershell
git tag -a v1.0.8 -m "TubeForge 1.0.8 desktop, 1.0.1 Android"
git push origin v1.0.8
```

## 4. Create the release

GitHub → **Releases** → **Draft a new release**:

- Choose tag `v1.0.8`
- Title: `TubeForge 1.0.8 (desktop) + 1.0.1 (Android)`
- Body: paste `RELEASE-NOTES.md`
- Attach `releases\TubeForge-Setup-1.0.8.exe`,
  `releases\TubeForge-Android-1.0.1.apk` and `releases\SHA256SUMS.txt`
- Publish

That step is also what satisfies the GPL: the binaries and the matching source are
published together at the same tag.

## 5. After publishing

- Pin the release; add a repo description and topics (`yt-dlp`, `pyside6`, `kotlin`,
  `android`, `ffmpeg`, `downloader`).
- Enable **Issues**; add a short `SECURITY.md` only if you want private reports.
- Never commit the debug keystore (`~/.android/debug.keystore`) or `local.properties`.
- If a site breaks extraction, rebuild after updating yt-dlp and cut a new tag — the
  GPL obligation repeats for every binary you publish.

## What is in here

```
README.md               the page people see (already references every file below)
RELEASE-NOTES.md        paste into the GitHub Release body
PUBLISHING.md           this file
LICENSE                 GPL-3.0 full text
THIRD-PARTY-NOTICES.md  component list + source offer (GPL-3.0 §6)
PRIVACY.md              network/storage behaviour
.gitignore              keeps keystores, local paths, build output out of git
.gitattributes          line endings (gradlew stays LF)
docs/                   7 screenshots used by README.md
desktop/                Windows app source + installer script (ffmpeg binaries excluded)
mobile/                 Android app source + Gradle wrapper
releases/               the two binaries + SHA256SUMS + upload note  [binaries git-ignored]
```
