# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Endpoint Toolbox Windows portable build.

Build with (from the repository root, on Windows):

    pyinstaller --noconfirm --clean packaging/windows/EndpointToolbox.spec

or simply run scripts/build_windows.ps1, which does this plus the dependency
install and test run. See docs/PACKAGING.md for the full rationale (onefile,
windowed/no console, keyring backend discovery, why no data files are needed
today).

PyInstaller only builds an executable for the platform it runs on: running this
spec on macOS/Linux produces a macOS/Linux binary, never a Windows .exe. It is
still useful there as a structural smoke test (import resolution, hidden
imports, hooks) - see docs/PACKAGING.md, "Build reel effectue".
"""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# SPECPATH is injected by PyInstaller into the spec's exec namespace and points
# at the directory containing this .spec file (packaging/windows).
ROOT_DIR = Path(SPECPATH).resolve().parent.parent  # noqa: F821 - SPECPATH is PyInstaller-injected

MAIN_SCRIPT = str(ROOT_DIR / "main.py")

ICON_PATH = ROOT_DIR / "resources" / "windows" / "app.ico"
icon_file = str(ICON_PATH) if ICON_PATH.exists() else None

VERSION_FILE_PATH = ROOT_DIR / "packaging" / "windows" / "version_info.txt"
version_file = str(VERSION_FILE_PATH) if sys.platform == "win32" and VERSION_FILE_PATH.exists() else None

# keyring discovers its backends (Keychain, Windows Credential Manager, ...) via
# package entry points at runtime. A frozen build has neither the package's
# .dist-info metadata nor an import mechanism that finds backend modules unless
# both are made explicit here - a well-known PyInstaller/keyring gap.
hidden_imports = collect_submodules("keyring.backends")
datas = copy_metadata("keyring")

block_cipher = None

a = Analysis(
    [MAIN_SCRIPT],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EndpointToolbox",
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
    icon=icon_file,
    version=version_file,
)
