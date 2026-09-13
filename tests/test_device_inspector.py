from __future__ import annotations

from app.graph.client import GraphReadOnlyClient
from app.graph.config import GraphConfigStore
from app.graph.errors import GraphConfigurationError
from app.graph.factory import build_intune_device_inspector
from app.graph.models import GraphSettings
from app.intune.device_inspector import IntuneDeviceInspectorService, detect_device_issues, parse_managed_device


class FakeGraphClient:
    def __init__(self):
        self.calls = []

    def get_all(self, path, *, params=None, cancellation=None):
        self.calls.append((path, params))
        return type(
            "GraphResponse",
            (),
            {
                "data": {
                    "value": [
                        {
                            "id": "device-1",
                            "deviceName": "LAPTOP-001",
                            "serialNumber": "SERIAL1",
                            "userPrincipalName": "user@example.com",
                            "operatingSystem": "Windows",
                            "complianceState": "compliant",
                            "lastSyncDateTime": "2026-09-13T10:00:00Z",
                        }
                    ]
                },
                "pages": (),
                "log": type("Log", (), {"url": path, "status_code": 200, "duration_ms": 5, "object_count": 1})(),
            },
        )()

    def get(self, path, *, params=None, cancellation=None):
        self.calls.append((path, params))
        return type(
            "GraphResponse",
            (),
            {
                "data": managed_device_payload(),
                "log": type("Log", (), {"url": path, "status_code": 200, "duration_ms": 5, "object_count": None})(),
            },
        )()


def managed_device_payload() -> dict:
    return {
        "id": "device-1",
        "deviceName": "LAPTOP-001",
        "azureADDeviceId": "entra-1",
        "serialNumber": "SERIAL1",
        "manufacturer": "Dell",
        "model": "Latitude",
        "operatingSystem": "Windows",
        "osVersion": "10.0.22631",
        "userPrincipalName": "user@example.com",
        "managedDeviceOwnerType": "company",
        "managementAgent": "mdm",
        "deviceEnrollmentType": "windowsAzureADJoin",
        "complianceState": "compliant",
        "lastSyncDateTime": "2026-09-13T10:00:00Z",
        "enrolledDateTime": "2026-01-01T10:00:00Z",
        "deviceCategoryDisplayName": "Workstations",
        "isEncrypted": True,
        "jailBroken": "False",
    }


def test_device_search_uses_managed_devices_read_endpoint() -> None:
    graph = FakeGraphClient()
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    devices, logs = service.search_devices("LAPTOP")
    assert devices[0].device_name == "LAPTOP-001"
    assert graph.calls[0][0] == "deviceManagement/managedDevices"
    assert "contains(deviceName" in graph.calls[0][1]["$filter"]
    assert len(logs) == 1


def test_inspect_device_parses_managed_device() -> None:
    graph = FakeGraphClient()
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert result.device.device_name == "LAPTOP-001"
    assert result.device.entra_device_id == "entra-1"
    assert result.device.is_managed is True
    assert result.device.raw["id"] == "device-1"


def test_non_compliant_issue() -> None:
    device = parse_managed_device({**managed_device_payload(), "complianceState": "noncompliant"})
    issues = detect_device_issues(device)
    assert any(issue.severity == "CRITICAL" and "non-compliant" in issue.title for issue in issues)


def test_stale_device_issue() -> None:
    device = parse_managed_device({**managed_device_payload(), "lastSyncDateTime": "2020-01-01T00:00:00Z"})
    issues = detect_device_issues(device, stale_device_days=7)
    assert any("Last check-in" in issue.title and "7 days" in issue.reason for issue in issues)


def test_not_encrypted_and_missing_data_issues() -> None:
    device = parse_managed_device(
        {
            "id": "device-1",
            "deviceName": "LAPTOP-001",
            "complianceState": "unknown",
            "isEncrypted": False,
        },
        primary_users=(),
    )
    titles = {issue.title for issue in detect_device_issues(device)}
    assert "Device not encrypted" in titles
    assert "No primary user" in titles
    assert "OS information missing" in titles


def test_missing_secret_blocks_service_factory(tmp_path) -> None:
    config_path = tmp_path / "graph.json"
    config = GraphConfigStore(config_path)
    settings = GraphSettings("tenant", "client")
    config.save(settings)

    class EmptySecretStore:
        def get_secret(self, _settings):
            return None

    try:
        build_intune_device_inspector(config, EmptySecretStore())  # type: ignore[arg-type]
    except GraphConfigurationError as exc:
        assert "Client Secret" in str(exc)
    else:
        raise AssertionError("Expected GraphConfigurationError")
