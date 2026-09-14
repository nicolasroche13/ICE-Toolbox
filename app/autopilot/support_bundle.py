from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.autopilot.models import AutopilotDeviceHealth, AutopilotInspectorResult
from app.intune.support_bundle import _to_plain
from app.utils.files import non_overwriting_path
from app.utils.sanitize import sanitize_for_export


APP_VERSION = "phase-4"


def build_autopilot_support_bundle_payload(result: AutopilotInspectorResult) -> dict[str, Any]:
    health = result.health
    payload = {
        "endpoint_toolbox_version": APP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "identity": _to_plain(result.identity),
        "health": _health_summary(health),
        "issues": [_to_plain(issue) for issue in (health.issues if health else ())],
        "capabilities": [_to_plain(capability) for capability in health.capabilities] if health else [],
        "sources": [_to_plain(source) for source in health.sources] if health else [],
        "graph_diagnostics": [_to_plain(log) for log in result.endpoint_logs],
        "raw_sources": health.raw_sources if health else {},
    }
    return sanitize_for_export(payload)


def export_autopilot_support_bundle(result: AutopilotInspectorResult, output_dir: Path) -> Path:
    serial = result.identity.serial_number or "unknown"
    safe_serial = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in serial)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = non_overwriting_path(output_dir / f"EndpointToolbox-Autopilot-{safe_serial}-{timestamp}.zip")
    payload = build_autopilot_support_bundle_payload(result)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.json", json.dumps(payload, indent=2, sort_keys=True))
    return path


def _health_summary(health: AutopilotDeviceHealth | None) -> dict[str, Any]:
    if health is None:
        return {}
    return {
        "status": health.status,
        "registered": bool(health.identity.id),
        "profile_assigned": bool(health.profile and health.profile.assignment_status),
    }
