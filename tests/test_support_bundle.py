from __future__ import annotations

import json
import zipfile

from app.graph.models import GraphRequestLog
from app.intune.device_inspector import parse_managed_device
from app.intune.models import (
    Capability,
    ComplianceSummary,
    DeviceHealth,
    DeviceInspectorResult,
    SourceStatus,
)
from app.intune.support_bundle import build_support_bundle_payload, export_support_bundle


def _sample_result() -> DeviceInspectorResult:
    device = parse_managed_device(
        {
            "id": "device-1",
            "deviceName": "PC-MRS-001",
            "azureADDeviceId": "entra-device-id",
            "serialNumber": "SERIAL-001",
            "complianceState": "noncompliant",
            "lastSyncDateTime": "2020-01-01T00:00:00Z",
            "isEncrypted": False,
            # A defensive leak scenario: Graph should never return this, but the
            # sanitizer must still strip it if a tenant payload ever includes one.
            "clientSecret": "should-never-leak",
        }
    )
    health = DeviceHealth(
        intune_device=device,
        compliance=ComplianceSummary(state="noncompliant", detail="Detailed reason not available."),
        sources=(
            SourceStatus(
                name="Intune managedDevice",
                available=True,
                endpoint="deviceManagement/managedDevices/device-1",
                status_code=200,
                request_id="req-1",
                client_request_id="client-1",
                response_date="Sun, 13 Sep 2026 19:00:00 GMT",
            ),
        ),
        capabilities=(
            Capability(name="Intune Device", state="AVAILABLE", feature="Device identity", source="Intune managedDevice"),
        ),
        issues=device.issues,
        raw_sources={
            "Intune Managed Device": device.raw,
            "Auth": {"Authorization": "Bearer super-secret", "access_token": "token-value"},
        },
    )
    logs = (
        GraphRequestLog("GET", "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices/device-1", 200, 12, 1, request_id="req-1"),
    )
    return DeviceInspectorResult(device=device, endpoint_logs=logs, health=health)


def test_support_bundle_payload_redacts_secrets_and_tokens() -> None:
    payload = build_support_bundle_payload(_sample_result())
    serialized = json.dumps(payload)
    assert "should-never-leak" not in serialized
    assert "super-secret" not in serialized
    assert "token-value" not in serialized
    assert payload["raw_sources"]["Auth"]["Authorization"] == "[REDACTED]"
    assert payload["raw_sources"]["Auth"]["access_token"] == "[REDACTED]"
    assert payload["raw_sources"]["Intune Managed Device"]["clientSecret"] == "[REDACTED]"


def test_support_bundle_payload_contains_expected_sections() -> None:
    payload = build_support_bundle_payload(_sample_result())
    assert payload["health"]["status"] in {"HEALTHY", "ATTENTION", "DEGRADED", "UNKNOWN"}
    assert isinstance(payload["capabilities"], list) and payload["capabilities"]
    assert isinstance(payload["sources"], list) and payload["sources"]
    assert isinstance(payload["graph_diagnostics"], list) and payload["graph_diagnostics"]
    assert payload["graph_diagnostics"][0]["request_id"] == "req-1"


def test_export_support_bundle_writes_sanitized_zip(tmp_path) -> None:
    path = export_support_bundle(_sample_result(), tmp_path)
    assert path.exists()
    assert path.suffix == ".zip"
    with zipfile.ZipFile(path) as archive:
        content = archive.read("diagnostics.json").decode("utf-8")
    assert "should-never-leak" not in content
    assert "super-secret" not in content
    assert "token-value" not in content


def test_export_support_bundle_does_not_overwrite_existing_export(tmp_path) -> None:
    first = export_support_bundle(_sample_result(), tmp_path)
    second = export_support_bundle(_sample_result(), tmp_path)
    assert first.exists()
    assert second.exists()
    assert first != second
