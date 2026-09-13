from __future__ import annotations

import json
import zipfile
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.intune.models import DeviceHealth, DeviceInspectorResult
from app.utils.files import non_overwriting_path
from app.utils.sanitize import sanitize_for_export


APP_VERSION = "phase-3.1"


def build_support_bundle_payload(result: DeviceInspectorResult) -> dict[str, Any]:
    health = result.health
    payload = {
        "endpoint_toolbox_version": APP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "device": _to_plain(result.device),
        "health": _health_summary(health),
        "issues": [_to_plain(issue) for issue in result.device.issues],
        "capabilities": [_to_plain(capability) for capability in health.capabilities] if health else [],
        "sources": [_to_plain(source) for source in health.sources] if health else [],
        "graph_diagnostics": [_to_plain(log) for log in result.endpoint_logs],
        "raw_sources": health.raw_sources if health else {"Intune Managed Device": result.device.raw},
    }
    return sanitize_for_export(payload)


def export_support_bundle(result: DeviceInspectorResult, output_dir: Path) -> Path:
    device_name = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in result.device.device_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = non_overwriting_path(output_dir / f"EndpointToolbox-{device_name}-{timestamp}.zip")
    payload = build_support_bundle_payload(result)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.json", json.dumps(payload, indent=2, sort_keys=True))
    return path


def _health_summary(health: DeviceHealth | None) -> dict[str, Any]:
    if health is None:
        return {}
    return {
        "status": health.status,
        "failed_applications": len(health.failed_applications),
        "application_deployment_status_available": any(app.kind == "deployment_status" for app in health.applications),
    }


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, tuple):
        return [_to_plain(item) for item in value]
    if isinstance(value, list):
        return [_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    return value
