from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.graph.errors import GraphForbiddenError, GraphNotFoundError
from app.graph.models import GraphRequestLog, GraphResponse
from app.intune.device_inspector import IntuneDeviceInspectorService
from app.intune.health import generate_device_issues, parse_application_status
from app.intune.models import ApplicationStatus, DeviceHealth
from app.utils.time import parse_graph_datetime


UUID = "11111111-1111-1111-1111-111111111111"


class HealthFakeGraphClient:
    def __init__(
        self,
        *,
        entra_forbidden: bool = False,
        entra_missing: bool = False,
        entra_ambiguous: bool = False,
        apps_forbidden: bool = False,
        apps_not_found: bool = False,
        app_failures_unavailable: bool = False,
        name_results: list[dict[str, Any]] | None = None,
        device_kwargs: dict[str, Any] | None = None,
    ):
        self.entra_forbidden = entra_forbidden
        self.entra_missing = entra_missing
        self.entra_ambiguous = entra_ambiguous
        self.apps_forbidden = apps_forbidden
        self.apps_not_found = apps_not_found
        self.app_failures_unavailable = app_failures_unavailable
        self.name_results = name_results
        self.device_kwargs = device_kwargs or {}
        self.calls: list[tuple[str, dict[str, str] | None]] = []

    def get(self, path: str, *, params=None, cancellation=None):  # noqa: ANN001
        self.calls.append((path, params))
        if path == f"deviceManagement/managedDevices/{UUID}":
            return graph_response(managed_device_payload(id=UUID, **self.device_kwargs), path)
        if path.startswith("deviceManagement/managedDevices/"):
            return graph_response(managed_device_payload(**self.device_kwargs), path)
        raise GraphNotFoundError("not found", status_code=404)

    def get_all(self, path: str, *, params=None, cancellation=None):  # noqa: ANN001
        self.calls.append((path, params))
        filter_value = (params or {}).get("$filter", "")
        if path == "deviceManagement/managedDevices":
            if "contains(deviceName" in filter_value:
                return graph_response(
                    {"value": self.name_results if self.name_results is not None else [managed_device_payload(**self.device_kwargs)]},
                    path,
                    object_count=1,
                )
            if "tolower(serialNumber)" in filter_value:
                return graph_response({"value": [managed_device_payload(serial="SERIAL-001")]}, path, object_count=1)
            if "tolower(azureADDeviceId)" in filter_value:
                return graph_response({"value": [managed_device_payload(entra_id=UUID)]}, path, object_count=1)
        if path.endswith("/users"):
            return graph_response({"value": [{"id": "user-1", "userPrincipalName": "user@example.com"}]}, path, object_count=1)
        if path == "devices":
            if self.entra_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if self.entra_ambiguous:
                values = [entra_payload(directory_id="directory-object-1"), entra_payload(directory_id="directory-object-2")]
                return graph_response({"value": values}, path, object_count=len(values))
            values = [] if self.entra_missing else [entra_payload()]
            return graph_response({"value": values}, path, object_count=len(values))
        if path.endswith("/detectedApps"):
            if self.apps_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if self.apps_not_found:
                raise GraphNotFoundError("not found", status_code=404)
            return graph_response({"value": [{"id": "app-1", "displayName": "Microsoft Edge", "version": "130"}]}, path, object_count=1)
        if path.endswith("deviceManagement/mobileAppTroubleshootingEvents"):
            if self.app_failures_unavailable:
                raise GraphNotFoundError("not found", status_code=404)
            return graph_response(
                {
                    "value": [
                        {
                            "id": "failure-1",
                            "applicationName": "FortiClient VPN",
                            "installState": "failed",
                            "troubleshootingErrorDetails": {"hexErrorCode": "0x80070643"},
                        }
                    ]
                },
                path,
                object_count=1,
            )
        return graph_response({"value": []}, path, object_count=0)


def graph_response(data: dict[str, Any], url: str, *, object_count: int | None = None) -> GraphResponse:
    return GraphResponse(data=data, log=GraphRequestLog("GET", url, 200, 10, object_count))


def managed_device_payload(
    *,
    id: str = "device-1",
    serial: str | None = "SERIAL-001",
    entra_id: str | None = "entra-device-id",
    compliant: str | None = "noncompliant",
    encrypted: bool | None = False,
    last_sync: str | None = "2020-01-01T00:00:00Z",
    enrolled: str | None = "2019-01-01T00:00:00Z",
) -> dict[str, Any]:
    return {
        "id": id,
        "deviceName": "PC-MRS-001",
        "azureADDeviceId": entra_id,
        "serialNumber": serial,
        "manufacturer": "Dell",
        "model": "Latitude 5450",
        "operatingSystem": "Windows",
        "osVersion": "10.0.26100",
        "userPrincipalName": "user@example.com",
        "managementAgent": "mdm",
        "deviceEnrollmentType": "windowsAzureADJoin",
        "complianceState": compliant,
        "lastSyncDateTime": last_sync,
        "enrolledDateTime": enrolled,
        "isEncrypted": encrypted,
    }


def entra_payload(*, enabled: bool = True, directory_id: str = "directory-object-id") -> dict[str, Any]:
    return {
        "id": directory_id,
        "deviceId": "entra-device-id",
        "displayName": "PC-MRS-001",
        "accountEnabled": enabled,
        "operatingSystem": "Windows",
        "operatingSystemVersion": "10.0.26100",
        "trustType": "AzureAd",
    }


def test_search_by_serial_when_name_has_no_result() -> None:
    graph = HealthFakeGraphClient(name_results=[])
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    devices, _logs = service.search_devices("SERIAL-001")
    assert devices[0].serial_number == "SERIAL-001"
    assert any(call[1] and "tolower(serialNumber)" in call[1].get("$filter", "") for call in graph.calls)


def test_search_by_intune_managed_device_id() -> None:
    graph = HealthFakeGraphClient()
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    devices, _logs = service.search_devices(UUID)
    assert devices[0].id == UUID
    assert graph.calls[0][0] == f"deviceManagement/managedDevices/{UUID}"


def test_search_by_serial_is_case_insensitive_and_trimmed() -> None:
    graph = HealthFakeGraphClient(name_results=[])
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    service.search_devices("  Serial-001  ")
    serial_call = next(call for call in graph.calls if call[1] and "tolower(serialNumber)" in call[1].get("$filter", ""))
    assert serial_call[1]["$filter"] == "tolower(serialNumber) eq 'serial-001'"


def test_duplicate_serial_number_devices_are_not_collapsed() -> None:
    duplicates = [
        managed_device_payload(id="device-a", serial="SERIAL-DUP"),
        managed_device_payload(id="device-b", serial="SERIAL-DUP"),
    ]
    graph = HealthFakeGraphClient(name_results=duplicates)
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    devices, _logs = service.search_devices("PC-MRS-001")
    assert {device.id for device in devices} == {"device-a", "device-b"}


def test_inspect_builds_consolidated_device_health() -> None:
    graph = HealthFakeGraphClient()
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert result.health is not None
    assert result.health.entra_device is not None
    assert result.health.entra_device.display_name == "PC-MRS-001"
    assert {app.name for app in result.health.applications} == {"Microsoft Edge", "FortiClient VPN"}
    assert "Intune Managed Device" in result.health.raw_sources
    assert "Entra Device" in result.health.raw_sources
    assert any(source.name == "Applications" and source.available for source in result.health.sources)


def test_entra_missing_creates_issue_without_breaking_inspector() -> None:
    graph = HealthFakeGraphClient(entra_missing=True)
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert result.health is not None
    assert result.health.entra_device is None
    assert any(issue.id == "entra.not_found" for issue in result.health.issues)


def test_entra_ambiguous_match_does_not_pick_arbitrary_device() -> None:
    graph = HealthFakeGraphClient(entra_ambiguous=True)
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert result.health is not None
    assert result.health.entra_device is None
    assert any(issue.id == "entra.ambiguous" for issue in result.health.issues)
    assert not any(issue.id == "entra.not_found" for issue in result.health.issues)


def test_partial_403_is_permission_aware_not_global_failure() -> None:
    graph = HealthFakeGraphClient(entra_forbidden=True)
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert result.health is not None
    assert result.health.intune_device.device_name == "PC-MRS-001"
    entra_source = next(source for source in result.health.sources if source.name == "Entra device")
    assert entra_source.permission_missing is True
    assert not any(issue.id == "entra.not_found" for issue in result.health.issues)
    entra_capability = next(cap for cap in result.health.capabilities if cap.name == "Entra Device")
    assert entra_capability.state == "PERMISSION_MISSING"


def test_partial_404_on_optional_source_does_not_break_inspector() -> None:
    graph = HealthFakeGraphClient(apps_not_found=True)
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert result.health is not None
    assert result.health.intune_device.device_name == "PC-MRS-001"
    apps_source = next(source for source in result.health.sources if source.name == "Applications")
    assert apps_source.available is False
    detected_apps_capability = next(cap for cap in result.health.capabilities if cap.name == "Detected Apps")
    assert detected_apps_capability.state == "API_UNAVAILABLE"


def test_beta_endpoint_unavailable_marks_capability_and_does_not_break_inspection() -> None:
    graph = HealthFakeGraphClient(app_failures_unavailable=True)
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert result.health is not None
    assert {app.name for app in result.health.applications} == {"Microsoft Edge"}
    deployment_status_capability = next(cap for cap in result.health.capabilities if cap.name == "Deployment Status")
    assert deployment_status_capability.state == "API_UNAVAILABLE"
    failures_source = next(source for source in result.health.sources if source.name == "Application failures")
    assert "/beta/" in failures_source.endpoint


def test_deployment_status_capability_is_partial_when_available() -> None:
    graph = HealthFakeGraphClient()
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    deployment_status_capability = next(cap for cap in result.health.capabilities if cap.name == "Deployment Status")  # type: ignore[union-attr]
    assert deployment_status_capability.state == "PARTIAL"
    detected_apps_capability = next(cap for cap in result.health.capabilities if cap.name == "Detected Apps")  # type: ignore[union-attr]
    assert detected_apps_capability.state == "AVAILABLE"


def test_application_failed_state_and_error_code_decimal() -> None:
    app = parse_application_status(
        {
            "applicationName": "Adobe Acrobat",
            "installState": "failed",
            "troubleshootingErrorDetails": {"hexErrorCode": "0x80070643"},
        }
    )
    assert app.install_state == "failed"
    assert app.error_code == "0x80070643"
    assert app.error_decimal == 2147944003


def test_detected_apps_do_not_count_as_deployment_status_failures() -> None:
    detected_failed_looking = ApplicationStatus(
        id="detected-1",
        name="Some Tool",
        version="1.0",
        install_state="failed",
        kind="detected_app",
    )
    health = DeviceHealth(
        intune_device=IntuneDeviceInspectorService(HealthFakeGraphClient()).inspect_device("device-1").device,  # type: ignore[arg-type]
        applications=(detected_failed_looking,),
    )
    assert health.failed_applications == ()
    issues = generate_device_issues(health)
    assert not any(issue.id == "apps.install_failed" for issue in issues)


def test_device_health_issue_generation_and_severity() -> None:
    graph = HealthFakeGraphClient()
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    issue_ids = {issue.id for issue in result.health.issues}  # type: ignore[union-attr]
    assert "intune.non_compliant" in issue_ids
    assert "intune.stale_check_in" in issue_ids
    assert "intune.not_encrypted" in issue_ids
    assert "apps.install_failed" in issue_ids
    assert result.health.status == "DEGRADED"  # type: ignore[union-attr]


def test_disabled_entra_device_rule() -> None:
    health = DeviceHealth(
        intune_device=IntuneDeviceInspectorService(HealthFakeGraphClient()).inspect_device("device-1").device,  # type: ignore[arg-type]
        entra_device=type(
            "Entra",
            (),
            {"account_enabled": False, "raw": {}, "device_id": "entra-device-id"},
        )(),
    )
    issues = generate_device_issues(health)
    assert any(issue.id == "entra.disabled" and issue.severity == "ERROR" for issue in issues)


def test_missing_compliance_state_does_not_create_non_compliant_issue() -> None:
    graph = HealthFakeGraphClient(device_kwargs={"compliant": None})
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert not any(issue.id == "intune.non_compliant" for issue in result.health.issues)  # type: ignore[union-attr]


def test_missing_encryption_flag_does_not_create_not_encrypted_issue() -> None:
    graph = HealthFakeGraphClient(device_kwargs={"encrypted": None})
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert not any(issue.id == "intune.not_encrypted" for issue in result.health.issues)  # type: ignore[union-attr]


def test_encrypted_false_still_creates_not_encrypted_issue() -> None:
    graph = HealthFakeGraphClient(device_kwargs={"encrypted": False})
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert any(issue.id == "intune.not_encrypted" for issue in result.health.issues)  # type: ignore[union-attr]


def test_null_last_sync_date_does_not_crash_or_create_stale_issue() -> None:
    graph = HealthFakeGraphClient(device_kwargs={"last_sync": None})
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert not any(issue.id == "intune.stale_check_in" for issue in result.health.issues)  # type: ignore[union-attr]


def test_recent_check_in_is_not_flagged_as_stale() -> None:
    recent = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    graph = HealthFakeGraphClient(device_kwargs={"last_sync": recent})
    service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device("device-1")
    assert not any(issue.id == "intune.stale_check_in" for issue in result.health.issues)  # type: ignore[union-attr]


def test_timezone_offset_date_is_normalized_to_utc() -> None:
    naive_utc = parse_graph_datetime("2024-01-01T12:00:00Z")
    offset = parse_graph_datetime("2024-01-01T14:00:00+02:00")
    assert naive_utc == offset
    assert offset.tzinfo is not None


def test_naive_date_without_timezone_is_assumed_utc_not_local() -> None:
    parsed = parse_graph_datetime("2024-01-01T12:00:00")
    assert parsed.utcoffset().total_seconds() == 0
    assert parsed.hour == 12
