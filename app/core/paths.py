"""Central path resolution: development vs PyInstaller-frozen, and per-OS user data locations.

This is the only module allowed to touch ``sys.frozen`` / ``sys._MEIPASS`` directly -
every other module resolves paths through the functions below instead of repeating
that check itself.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "EndpointToolbox"
LEGACY_UNIX_DIR_NAME = ".endpoint_toolbox"


def is_frozen() -> bool:
    """True when running from a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False))


def frozen_resource_root() -> Path:
    """Base directory for bundled resources when frozen.

    ``sys._MEIPASS`` is set by PyInstaller's onefile bootloader and points at the
    temporary extraction directory; a onedir build has no ``_MEIPASS`` and bundled
    files sit next to the executable instead.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(sys.executable).resolve().parent


def resource_path(*parts: str) -> Path:
    """Resolve a bundled resource (icon, template, static data) in dev or frozen mode.

    Nothing in the codebase currently ships such a resource, but UI code should use
    this helper - instead of a raw relative path or ``Path(__file__)`` - as soon as one
    is added, so resolution stays correct after freezing without touching every call site.
    """
    if is_frozen():
        base = frozen_resource_root()
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return base.joinpath(*parts)


def user_data_dir() -> Path:
    """Per-user directory for non-secret configuration data.

    Never next to the executable or under Program Files: on Windows this resolves to
    ``%APPDATA%\\EndpointToolbox``; macOS and Linux keep the pre-existing
    ``~/.endpoint_toolbox`` location unchanged.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / APP_DIR_NAME
    return Path.home() / LEGACY_UNIX_DIR_NAME


def user_log_dir() -> Path:
    """Per-user directory for log files, alongside the configuration directory."""
    return user_data_dir() / "logs"
