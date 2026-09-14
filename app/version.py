"""Single source of truth for the Endpoint Toolbox application version.

Used by the Windows packaging metadata (packaging/windows/version_info.txt).
Not related to the per-module ``APP_VERSION`` phase markers embedded in each
Support Bundle export (app/intune, app/autopilot, app/entra, app/workspace) -
those track which module implementation produced a given bundle and are left
untouched.
"""
from __future__ import annotations

__version__ = "0.7.0"
