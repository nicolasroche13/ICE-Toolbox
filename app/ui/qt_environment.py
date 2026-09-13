from __future__ import annotations

import os
from pathlib import Path


def configure_qt_plugin_path() -> None:
    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH"):
        return
    try:
        import PySide6
    except Exception:
        return
    plugin_path = Path(PySide6.__file__).resolve().parent / "Qt" / "plugins" / "platforms"
    if plugin_path.exists():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugin_path)
