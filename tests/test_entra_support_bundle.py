from __future__ import annotations

import json
import zipfile

from app.entra.health import parse_entra_device_detail
from app.entra.models import EntraDeviceHealth, EntraInspectorResult
from app.entra.support_bundle import build_entra_support_bundle_payload, export_entra_support_bundle
from app.graph.models import GraphRequestLog
from app.intune.models import Capability, SourceStatus


def _sample_result() -> EntraInspectorResult:
    device = parse_entra_device_detail(
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "deviceId": "33333333-3333-3333-3333-333333333333",
            "displayName": "PC-MRS-0042",
            "accountEnabled": True,
            # Defensive leak scenario: Graph should never return this, but the
            # sanitizer must still strip it if a tenant payload ever includes one.
            "clientSecret": "should-never-leak",
        }
    )
    health = EntraDeviceHealth(
        device=device,
        sources=(
            SourceStatus(
                name="Entra device",
                available=True,
                endpoint="devices/22222222-2222-2222-2222-222222222222",
                status_code=200,
                request_id="req-1",
            ),
        ),
        capabilities=(
            Capability(name="Entra Device", state="AVAILABLE", feature="Identite", source="Entra device"),
        ),
        raw_sources={
            "Entra Device": device.raw,
            "Auth": {"Authorization": "Bearer super-secret", "access_token": "token-value"},
        },
    )
    logs = (
        GraphRequestLog(
            "GET",
            "https://graph.microsoft.com/v1.0/devices/22222222-2222-2222-2222-222222222222",
            200,
            12,
            1,
            request_id="req-1",
        ),
    )
    return EntraInspectorResult(device=device, endpoint_logs=logs, health=health)


def test_entra_support_bundle_payload_redacts_secrets_and_tokens() -> None:
    payload = build_entra_support_bundle_payload(_sample_result())
    serialized = json.dumps(payload)
    assert "should-never-leak" not in serialized
    assert "super-secret" not in serialized
    assert "token-value" not in serialized
    assert payload["raw_sources"]["Auth"]["Authorization"] == "[REDACTED]"
    assert payload["raw_sources"]["Entra Device"]["clientSecret"] == "[REDACTED]"


def test_entra_support_bundle_payload_contains_expected_sections() -> None:
    payload = build_entra_support_bundle_payload(_sample_result())
    assert payload["health"]["status"] in {"HEALTHY", "ATTENTION", "DEGRADED", "UNKNOWN"}
    assert isinstance(payload["capabilities"], list) and payload["capabilities"]
    assert isinstance(payload["sources"], list) and payload["sources"]
    assert isinstance(payload["graph_diagnostics"], list) and payload["graph_diagnostics"]
    assert payload["graph_diagnostics"][0]["request_id"] == "req-1"
    assert payload["device"]["display_name"] == "PC-MRS-0042"


def test_export_entra_support_bundle_writes_sanitized_zip(tmp_path) -> None:
    path = export_entra_support_bundle(_sample_result(), tmp_path)
    assert path.exists()
    assert path.name.startswith("EndpointToolbox-Entra-PC-MRS-0042-")
    with zipfile.ZipFile(path) as archive:
        content = archive.read("diagnostics.json").decode("utf-8")
    assert "should-never-leak" not in content
    assert "super-secret" not in content
    assert "token-value" not in content


def test_export_entra_support_bundle_does_not_overwrite_existing_export(tmp_path) -> None:
    first = export_entra_support_bundle(_sample_result(), tmp_path)
    second = export_entra_support_bundle(_sample_result(), tmp_path)
    assert first.exists()
    assert second.exists()
    assert first != second
