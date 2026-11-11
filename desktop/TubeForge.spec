# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH)

# yt-dlp uses curl_cffi for browser impersonation (Cloudflare/anti-bot sites).
curl_datas, curl_binaries, curl_hidden = collect_all("curl_cffi")

# Work around a CPython 3.10.0 dis bug that crashes PyInstaller's analysis.
# See build/cpython_dis_fix.py; remove once the build interpreter is >= 3.10.1.
sys.path.insert(0, str(ROOT / "build"))
import cpython_dis_fix  # noqa: E402,F401

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    binaries=curl_binaries,
    datas=[
        (str(ROOT / "assets" / "icon.ico"), "assets"),
        (str(ROOT / "assets" / "logo.png"), "assets"),
    ] + curl_datas,
    hiddenimports=[
        "Cryptodome",
        "mutagen",
        "brotli",
        "certifi",
        "websockets",
        "requests",
        "urllib3",
        "PySide6.QtSvg",
        "PySide6.QtNetwork",
    ] + curl_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "torch",
        "torchvision",
        "PIL",
        "wx",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "IPython",
        "notebook",
        "jupyter",
        "pytest",
        "werkzeug",
        "flask",
        "jinja2",
        "markupsafe",
        "itsdangerous",
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="TubeForge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icon.ico"),
    version=str(ROOT / "build" / "version_info.txt"),
)
