from __future__ import annotations

import json
import zipfile

from app.autopilot.health import parse_autopilot_identity, parse_autopilot_profile
from app.autopilot.models import AutopilotDeviceHealth, AutopilotInspectorResult
from app.autopilot.support_bundle import build_autopilot_support_bundle_payload, export_autopilot_support_bundle
from app.graph.models import GraphRequestLog
from app.intune.models import Capability, SourceStatus


def _sample_result() -> AutopilotInspectorResult:
    identity = parse_autopilot_identity(
        {
            "id": "22222222-2222-2222-2222-222222222222",
            "serialNumber": "PF123456",
            "groupTag": "PROD-MRS",
            "managedDeviceId": "device-1",
            "azureActiveDirectoryDeviceId": "entra-device-id",
            "displayName": "PC-MRS-0042",
            # Defensive leak scenario: Graph should never return this, but the
            # sanitizer must still strip it if a tenant payload ever includes one.
            "clientSecret": "should-never-leak",
        }
    )
    profile = parse_autopilot_profile(
        {
            "deploymentProfileAssignmentStatus": "assignedInSync",
            "deploymentProfile": {"id": "profile-1", "displayName": "Windows 11 Corporate"},
        }
    )
    health = AutopilotDeviceHealth(
        identity=identity,
        profile=profile,
        sources=(
            SourceStatus(
                name="Autopilot identity",
                available=True,
                endpoint="deviceManagement/windowsAutopilotDeviceIdentities/22222222-2222-2222-2222-222222222222",
                status_code=200,
                request_id="req-1",
            ),
        ),
        capabilities=(
            Capability(name="Autopilot Identity", state="AVAILABLE", feature="Identite", source="Autopilot identity"),
        ),
        raw_sources={
            "Autopilot": identity.raw,
            "Auth": {"Authorization": "Bearer super-secret", "access_token": "token-value"},
        },
    )
    logs = (
        GraphRequestLog(
            "GET",
            "https://graph.microsoft.com/v1.0/deviceManagement/windowsAutopilotDeviceIdentities/22222222-2222-2222-2222-222222222222",
            200,
            12,
            1,
            request_id="req-1",
        ),
    )
    return AutopilotInspectorResult(identity=identity, endpoint_logs=logs, health=health)


def test_autopilot_support_bundle_payload_redacts_secrets_and_tokens() -> None:
    payload = build_autopilot_support_bundle_payload(_sample_result())
    serialized = json.dumps(payload)
    assert "should-never-leak" not in serialized
    assert "super-secret" not in serialized
    assert "token-value" not in serialized
    assert payload["raw_sources"]["Auth"]["Authorization"] == "[REDACTED]"
    assert payload["raw_sources"]["Autopilot"]["clientSecret"] == "[REDACTED]"


def test_autopilot_support_bundle_payload_contains_expected_sections() -> None:
    payload = build_autopilot_support_bundle_payload(_sample_result())
    assert payload["health"]["status"] in {"HEALTHY", "ATTENTION", "DEGRADED", "UNKNOWN"}
    assert payload["health"]["registered"] is True
    assert isinstance(payload["capabilities"], list) and payload["capabilities"]
    assert isinstance(payload["sources"], list) and payload["sources"]
    assert isinstance(payload["graph_diagnostics"], list) and payload["graph_diagnostics"]
    assert payload["graph_diagnostics"][0]["request_id"] == "req-1"
    assert payload["identity"]["serial_number"] == "PF123456"


def test_export_autopilot_support_bundle_writes_sanitized_zip_named_with_serial(tmp_path) -> None:
    path = export_autopilot_support_bundle(_sample_result(), tmp_path)
    assert path.exists()
    assert path.name.startswith("EndpointToolbox-Autopilot-PF123456-")
    with zipfile.ZipFile(path) as archive:
        content = archive.read("diagnostics.json").decode("utf-8")
    assert "should-never-leak" not in content
    assert "super-secret" not in content
    assert "token-value" not in content


def test_export_autopilot_support_bundle_does_not_overwrite_existing_export(tmp_path) -> None:
    first = export_autopilot_support_bundle(_sample_result(), tmp_path)
    second = export_autopilot_support_bundle(_sample_result(), tmp_path)
    assert first.exists()
    assert second.exists()
    assert first != second
