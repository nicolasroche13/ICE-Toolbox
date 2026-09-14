from __future__ import annotations

import re
from typing import Any

from app.autopilot.inspector import AutopilotInspectorService
from app.graph.client import GRAPH_BETA_BASE_URL
from app.graph.errors import GraphForbiddenError, GraphNotFoundError, GraphThrottledError
from app.graph.models import GraphRequestLog, GraphResponse


AUTOPILOT_ID = "22222222-2222-2222-2222-222222222222"
MANAGED_DEVICE_ID = "44444444-4444-4444-4444-444444444444"
ENTRA_DEVICE_GUID = "33333333-3333-3333-3333-333333333333"


def graph_response(data: dict[str, Any], url: str, *, object_count: int | None = None) -> GraphResponse:
    return GraphResponse(data=data, log=GraphRequestLog("GET", url, 200, 10, object_count))


def autopilot_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": AUTOPILOT_ID,
        "groupTag": "PROD-MRS",
        "purchaseOrderIdentifier": "PO-1",
        "serialNumber": "PF123456",
        "manufacturer": "Dell",
        "model": "Latitude 5450",
        "enrollmentState": "enrolled",
        "lastContactedDateTime": "2026-09-01T00:00:00Z",
        "userPrincipalName": "user@example.com",
        "displayName": "PC-MRS-0042",
        "azureActiveDirectoryDeviceId": ENTRA_DEVICE_GUID,
        "managedDeviceId": MANAGED_DEVICE_ID,
    }
    payload.update(overrides)
    return payload


def managed_device_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": MANAGED_DEVICE_ID,
        "deviceName": "PC-MRS-0042",
        "azureADDeviceId": ENTRA_DEVICE_GUID,
        "serialNumber": "PF123456",
        "manufacturer": "Dell",
        "model": "Latitude 5450",
        "operatingSystem": "Windows",
        "osVersion": "10.0.26100",
        "userPrincipalName": "user@example.com",
        "managementAgent": "mdm",
        "deviceEnrollmentType": "windowsAzureADJoin",
        "complianceState": "compliant",
        "lastSyncDateTime": "2026-09-13T00:00:00Z",
        "enrolledDateTime": "2025-01-01T00:00:00Z",
        "isEncrypted": True,
    }
    payload.update(overrides)
    return payload


def entra_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": "directory-object-1",
        "deviceId": ENTRA_DEVICE_GUID,
        "displayName": "PC-MRS-0042",
        "accountEnabled": True,
        "operatingSystem": "Windows",
        "operatingSystemVersion": "10.0.26100",
        "trustType": "AzureAd",
    }
    payload.update(overrides)
    return payload


def profile_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": AUTOPILOT_ID,
        "deploymentProfileAssignmentStatus": "assignedInSync",
        "deploymentProfileAssignmentDetailedStatus": "none",
        "deploymentProfileAssignedDateTime": "2026-08-01T00:00:00Z",
        "deploymentProfile": {
            "id": "profile-1",
            "displayName": "Windows 11 Corporate",
            "description": "Profil standard",
            "deviceType": "windowsPc",
        },
    }
    payload.update(overrides)
    return payload


class AutopilotFakeGraphClient:
    def __init__(
        self,
        *,
        autopilot_forbidden: bool = False,
        autopilot_not_found: bool = False,
        serial_results: list[dict[str, Any]] | None = None,
        name_results: list[dict[str, Any]] | None = None,
        profile_not_found: bool = False,
        profile_forbidden: bool = False,
        profile_overrides: dict[str, Any] | None = None,
        intune_not_found: bool = False,
        intune_forbidden: bool = False,
        intune_throttled: bool = False,
        managed_device_overrides: dict[str, Any] | None = None,
        entra_forbidden: bool = False,
        entra_missing: bool = False,
        entra_ambiguous: bool = False,
    ):
        self.autopilot_forbidden = autopilot_forbidden
        self.autopilot_not_found = autopilot_not_found
        self.serial_results = serial_results
        self.name_results = name_results
        self.profile_not_found = profile_not_found
        self.profile_forbidden = profile_forbidden
        self.profile_overrides = profile_overrides or {}
        self.intune_not_found = intune_not_found
        self.intune_forbidden = intune_forbidden
        self.intune_throttled = intune_throttled
        self.managed_device_overrides = managed_device_overrides or {}
        self.entra_forbidden = entra_forbidden
        self.entra_missing = entra_missing
        self.entra_ambiguous = entra_ambiguous
        self.calls: list[tuple[str, dict[str, str] | None]] = []

    def get(self, path: str, *, params=None, cancellation=None):  # noqa: ANN001
        self.calls.append((path, params))
        if path.startswith(GRAPH_BETA_BASE_URL) and "windowsAutopilotDeviceIdentities" in path:
            if self.profile_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if self.profile_not_found:
                raise GraphNotFoundError("not found", status_code=404)
            return graph_response(profile_payload(**self.profile_overrides), path)
        if path == f"deviceManagement/windowsAutopilotDeviceIdentities/{AUTOPILOT_ID}":
            if self.autopilot_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if self.autopilot_not_found:
                raise GraphNotFoundError("not found", status_code=404)
            return graph_response(autopilot_payload(), path)
        if path.startswith("deviceManagement/windowsAutopilotDeviceIdentities/"):
            raise GraphNotFoundError("not found", status_code=404)
        if path == f"deviceManagement/managedDevices/{MANAGED_DEVICE_ID}":
            if self.intune_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if self.intune_not_found:
                raise GraphNotFoundError("not found", status_code=404)
            if self.intune_throttled:
                raise GraphThrottledError("throttled", status_code=429)
            return graph_response(managed_device_payload(**self.managed_device_overrides), path)
        if path.startswith("deviceManagement/managedDevices/"):
            raise GraphNotFoundError("not found", status_code=404)
        raise GraphNotFoundError("not found", status_code=404)

    def get_all(self, path: str, *, params=None, cancellation=None):  # noqa: ANN001
        self.calls.append((path, params))
        filter_value = (params or {}).get("$filter", "")
        if path == "deviceManagement/windowsAutopilotDeviceIdentities":
            if self.serial_results is not None:
                values = self.serial_results
            else:
                match = re.search(r"contains\(serialNumber,'(.*)'\)", filter_value)
                queried_serial = match.group(1) if match else ""
                values = [autopilot_payload()] if queried_serial == "PF123456" else []
            return graph_response({"value": values}, path, object_count=len(values))
        if path == "deviceManagement/managedDevices":
            if "contains(deviceName" in filter_value:
                values = self.name_results if self.name_results is not None else [managed_device_payload()]
                return graph_response({"value": values}, path, object_count=len(values))
            if "azureADDeviceId eq" in filter_value:
                return graph_response({"value": [managed_device_payload()]}, path, object_count=1)
            return graph_response({"value": []}, path, object_count=0)
        if path == "devices":
            if self.entra_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if self.entra_ambiguous:
                values = [entra_payload(id="d1"), entra_payload(id="d2")]
            elif self.entra_missing:
                values = []
            else:
                values = [entra_payload()]
            return graph_response({"value": values}, path, object_count=len(values))
        return graph_response({"value": []}, path, object_count=0)


# --- Search ---------------------------------------------------------------


def test_search_by_serial_number_finds_registered_device() -> None:
    graph = AutopilotFakeGraphClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    results, _logs = service.search_devices("PF123456")
    assert len(results) == 1
    assert results[0].id == AUTOPILOT_ID
    assert results[0].is_registered is True


def test_search_by_autopilot_id_direct_lookup() -> None:
    graph = AutopilotFakeGraphClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    results, _logs = service.search_devices(AUTOPILOT_ID)
    assert len(results) == 1
    assert results[0].id == AUTOPILOT_ID
    assert graph.calls[0][0] == f"deviceManagement/windowsAutopilotDeviceIdentities/{AUTOPILOT_ID}"


def test_search_unknown_serial_returns_no_results() -> None:
    graph = AutopilotFakeGraphClient(serial_results=[], name_results=[])
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    results, _logs = service.search_devices("UNKNOWN-SERIAL")
    assert results == []


def test_search_serial_with_multiple_matches_returns_all_without_arbitrary_choice() -> None:
    duplicates = [
        autopilot_payload(id="a1", serialNumber="DUPLICATE"),
        autopilot_payload(id="a2", serialNumber="DUPLICATE"),
    ]
    graph = AutopilotFakeGraphClient(serial_results=duplicates)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    results, _logs = service.search_devices("DUPLICATE")
    assert {result.id for result in results} == {"a1", "a2"}


def test_search_by_device_name_bridges_through_intune_serial() -> None:
    graph = AutopilotFakeGraphClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    results, _logs = service.search_devices("PC-MRS-0042")
    assert len(results) == 1
    assert results[0].id == AUTOPILOT_ID
    assert any(call[0] == "deviceManagement/managedDevices" for call in graph.calls)


def test_search_by_managed_device_id_bridges_to_autopilot() -> None:
    graph = AutopilotFakeGraphClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    results, _logs = service.search_devices(MANAGED_DEVICE_ID)
    assert len(results) == 1
    assert results[0].id == AUTOPILOT_ID


def test_search_by_managed_device_id_not_registered_in_autopilot() -> None:
    graph = AutopilotFakeGraphClient(serial_results=[])
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    results, _logs = service.search_devices(MANAGED_DEVICE_ID)
    assert len(results) == 1
    assert results[0].id == ""
    assert results[0].is_registered is False
    assert results[0].serial_number == "PF123456"
    assert results[0].managed_device_id == MANAGED_DEVICE_ID


def test_search_by_entra_device_id_bridges_to_autopilot() -> None:
    graph = AutopilotFakeGraphClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    results, _logs = service.search_devices(ENTRA_DEVICE_GUID)
    assert len(results) == 1
    assert results[0].id == AUTOPILOT_ID


def test_search_trims_and_normalizes_serial_spaces() -> None:
    graph = AutopilotFakeGraphClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    service.search_devices("  PF 123456  ")
    filter_call = next(
        call
        for call in graph.calls
        if call[0] == "deviceManagement/windowsAutopilotDeviceIdentities" and call[1] and "contains(serialNumber" in (call[1].get("$filter") or "")
    )
    assert filter_call[1]["$filter"] == "contains(serialNumber,'PF123456')"


# --- Full inspection --------------------------------------------------------


def test_inspect_device_with_everything_present() -> None:
    graph = AutopilotFakeGraphClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    health = result.health
    assert health is not None
    assert health.identity.serial_number == "PF123456"
    assert health.identity.group_tag == "PROD-MRS"
    assert health.intune_device is not None
    assert health.intune_device.device_name == "PC-MRS-0042"
    assert health.entra_device is not None
    assert health.profile is not None
    assert health.profile.display_name == "Windows 11 Corporate"
    assert health.status == "HEALTHY"
    capability_names = {capability.name for capability in health.capabilities}
    assert {"Autopilot Identity", "Enrollment Information", "Autopilot Profile", "Intune Correlation", "Entra Correlation"} <= capability_names
    assert all(capability.state == "AVAILABLE" for capability in health.capabilities)


def test_autopilot_not_registered_issue_when_bridged_via_intune() -> None:
    graph = AutopilotFakeGraphClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(
        autopilot_id="", fallback_managed_device_id=MANAGED_DEVICE_ID, fallback_serial_number="PF123456"
    )
    health = result.health
    assert health is not None
    assert health.identity.id == ""
    assert health.intune_device is not None
    assert any(issue.id == "autopilot_not_registered" for issue in health.issues)
    autopilot_capability = next(c for c in health.capabilities if c.name == "Autopilot Identity")
    assert autopilot_capability.state == "UNAVAILABLE"


def test_group_tag_absent_does_not_create_any_issue() -> None:
    class NoGroupTagClient(AutopilotFakeGraphClient):
        def get(self, path, *, params=None, cancellation=None):  # noqa: ANN001
            if path == f"deviceManagement/windowsAutopilotDeviceIdentities/{AUTOPILOT_ID}":
                self.calls.append((path, params))
                return graph_response(autopilot_payload(groupTag=""), path)
            return super().get(path, params=params, cancellation=cancellation)

    graph = NoGroupTagClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert result.health is not None
    assert result.health.identity.group_tag is None
    assert not any("group" in issue.id.casefold() for issue in result.health.issues)


def test_intune_device_missing_when_managed_device_id_is_dangling() -> None:
    graph = AutopilotFakeGraphClient(intune_not_found=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    health = result.health
    assert health is not None
    assert health.intune_device is None
    assert any(issue.id == "intune_device_missing" for issue in health.issues)
    intune_capability = next(c for c in health.capabilities if c.name == "Intune Correlation")
    assert intune_capability.state == "API_UNAVAILABLE"


def test_intune_partial_403_does_not_break_inspection() -> None:
    graph = AutopilotFakeGraphClient(intune_forbidden=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    health = result.health
    assert health is not None
    assert health.identity.serial_number == "PF123456"
    assert health.intune_device is None
    intune_capability = next(c for c in health.capabilities if c.name == "Intune Correlation")
    assert intune_capability.state == "PERMISSION_MISSING"


def test_intune_throttled_is_treated_as_partial_failure() -> None:
    graph = AutopilotFakeGraphClient(intune_throttled=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    health = result.health
    assert health is not None
    assert health.identity.serial_number == "PF123456"
    intune_capability = next(c for c in health.capabilities if c.name == "Intune Correlation")
    assert intune_capability.state == "ERROR"


def test_entra_missing_creates_issue_without_breaking_inspection() -> None:
    graph = AutopilotFakeGraphClient(entra_missing=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    health = result.health
    assert health is not None
    assert health.entra_device is None
    assert any(issue.id == "entra_device_missing" for issue in health.issues)


def test_entra_partial_403_does_not_break_inspection() -> None:
    graph = AutopilotFakeGraphClient(entra_forbidden=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    health = result.health
    assert health is not None
    assert health.intune_device is not None
    assert health.entra_device is None
    entra_capability = next(c for c in health.capabilities if c.name == "Entra Correlation")
    assert entra_capability.state == "PERMISSION_MISSING"


def test_entra_ambiguous_creates_correlation_ambiguous_issue() -> None:
    graph = AutopilotFakeGraphClient(entra_ambiguous=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    health = result.health
    assert health is not None
    assert health.entra_device is None
    assert any(issue.id == "correlation_ambiguous" for issue in health.issues)
    assert not any(issue.id == "entra_device_missing" for issue in health.issues)


def test_entra_disabled_issue() -> None:
    graph = AutopilotFakeGraphClient()

    class DisabledEntraClient(AutopilotFakeGraphClient):
        def get_all(self, path, *, params=None, cancellation=None):  # noqa: ANN001
            if path == "devices":
                self.calls.append((path, params))
                return graph_response({"value": [entra_payload(accountEnabled=False)]}, path, object_count=1)
            return super().get_all(path, params=params, cancellation=cancellation)

    graph = DisabledEntraClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert any(issue.id == "entra_device_disabled" and issue.severity == "ERROR" for issue in result.health.issues)


def test_intune_stale_issue() -> None:
    graph = AutopilotFakeGraphClient(managed_device_overrides={"lastSyncDateTime": "2020-01-01T00:00:00Z"})
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert any(issue.id == "intune_device_stale" for issue in result.health.issues)


def test_identifier_mismatch_issue() -> None:
    graph = AutopilotFakeGraphClient(managed_device_overrides={"azureADDeviceId": "55555555-5555-5555-5555-555555555555"})
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert any(issue.id == "identifier_mismatch" for issue in result.health.issues)


def test_null_dates_do_not_crash() -> None:
    graph = AutopilotFakeGraphClient(managed_device_overrides={"lastSyncDateTime": None, "enrolledDateTime": None})
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert result.health is not None
    assert not any(issue.id == "intune_device_stale" for issue in result.health.issues)


# --- Profile assignment ------------------------------------------------------


def test_profile_assigned_in_sync_creates_no_issue() -> None:
    graph = AutopilotFakeGraphClient()
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert result.health.profile.assignment_status == "assignedInSync"
    assert not any(issue.id in {"profile_not_assigned", "profile_assignment_failed"} for issue in result.health.issues)


def test_profile_not_assigned_issue() -> None:
    graph = AutopilotFakeGraphClient(profile_overrides={"deploymentProfileAssignmentStatus": "notAssigned", "deploymentProfile": None})
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert any(issue.id == "profile_not_assigned" and issue.severity == "WARNING" for issue in result.health.issues)


def test_profile_unknown_status_creates_no_issue() -> None:
    graph = AutopilotFakeGraphClient(profile_overrides={"deploymentProfileAssignmentStatus": "unknown"})
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert not any(issue.id in {"profile_not_assigned", "profile_assignment_failed"} for issue in result.health.issues)


def test_profile_assignment_failed_issue() -> None:
    graph = AutopilotFakeGraphClient(
        profile_overrides={
            "deploymentProfileAssignmentStatus": "failed",
            "deploymentProfileAssignmentDetailedStatus": "hardwareRequirementsNotMet",
        }
    )
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert any(issue.id == "profile_assignment_failed" and issue.severity == "ERROR" for issue in result.health.issues)


def test_beta_profile_unavailable_marks_capability_and_does_not_break_inspection() -> None:
    graph = AutopilotFakeGraphClient(profile_not_found=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    health = result.health
    assert health is not None
    assert health.profile is None
    assert health.intune_device is not None
    profile_capability = next(c for c in health.capabilities if c.name == "Autopilot Profile")
    assert profile_capability.state == "API_UNAVAILABLE"
    profile_source = next(source for source in health.sources if source.name == "Autopilot profile")
    assert "/beta/" in profile_source.endpoint


def test_profile_permission_missing_capability() -> None:
    graph = AutopilotFakeGraphClient(profile_forbidden=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    profile_capability = next(c for c in result.health.capabilities if c.name == "Autopilot Profile")
    assert profile_capability.state == "PERMISSION_MISSING"


def test_critical_data_unavailable_when_all_secondary_sources_fail() -> None:
    graph = AutopilotFakeGraphClient(profile_forbidden=True, intune_forbidden=True, entra_forbidden=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    result = service.inspect_device(autopilot_id=AUTOPILOT_ID)
    assert any(issue.id == "critical_data_unavailable" and issue.severity == "ERROR" for issue in result.health.issues)


def test_autopilot_403_propagates_as_direct_error() -> None:
    graph = AutopilotFakeGraphClient(autopilot_forbidden=True)
    service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    try:
        service.inspect_device(autopilot_id=AUTOPILOT_ID)
    except GraphForbiddenError:
        pass
    else:
        raise AssertionError("Expected GraphForbiddenError to propagate")
