Bundled FFmpeg binaries
=======================

Source: https://github.com/FFmpeg-Builds/FFmpeg-Builds
Build:  ffmpeg-N-128718-gb2b543c079-win64-gpl-shared
        (autobuild-2026-11-09-12-42)

The installer copies the files in `bin/` to `<install>\ffmpeg\bin` and
`LICENSE.txt` to `<install>\ffmpeg`. TubeForge finds ffmpeg there
automatically, so users do not need a separate FFmpeg installation.

The shared build is used to keep the installer smaller. Keep the DLLs next to
ffmpeg.exe; ffmpeg and ffprobe load them from their own folder.

License: see LICENSE.txt (GPLv3 for this build).
