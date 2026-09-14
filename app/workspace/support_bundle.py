from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.intune.support_bundle import _to_plain
from app.utils.files import non_overwriting_path
from app.utils.sanitize import sanitize_for_export
from app.workspace.models import DeviceWorkspaceResult


APP_VERSION = "phase-6"


def build_workspace_support_bundle_payload(result: DeviceWorkspaceResult) -> dict[str, Any]:
    """One coherent, sanitized payload per logical file - not three module
    ZIPs nested inside one another. Each key becomes its own JSON entry in
    the exported archive, keeping provenance clear."""
    files = {
        "identity.json": _to_plain(result.resolved_identity),
        "health.json": {
            "endpoint_toolbox_version": APP_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "query": result.query,
            "anchor": result.anchor,
            "status": result.status,
        },
        "capabilities.json": {"capabilities": [_to_plain(capability) for capability in result.capabilities]},
        "autopilot.json": _to_plain(result.autopilot_block) if result.autopilot_block else {},
        "entra.json": _to_plain(result.entra_block) if result.entra_block else {},
        "intune.json": _to_plain(result.intune_block) if result.intune_block else {},
        "diagnostics.json": {
            "issues": [_to_plain(issue) for issue in result.issues],
            "sources": [_to_plain(source) for source in result.sources],
            "graph_diagnostics": [_to_plain(log) for log in result.endpoint_logs],
            "raw_sources": result.raw_sources,
        },
    }
    return {name: sanitize_for_export(content) for name, content in files.items()}


def export_workspace_support_bundle(result: DeviceWorkspaceResult, output_dir: Path) -> Path:
    name = result.resolved_identity.device_name or result.resolved_identity.serial_number or "unknown"
    safe_name = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = non_overwriting_path(output_dir / f"EndpointToolbox-Appareil-{safe_name}-{timestamp}.zip")
    payload = build_workspace_support_bundle_payload(result)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in payload.items():
            archive.writestr(filename, json.dumps(content, indent=2, sort_keys=True))
    return path
