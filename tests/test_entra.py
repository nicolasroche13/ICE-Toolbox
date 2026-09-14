from __future__ import annotations

import re
from typing import Any

from app.autopilot.inspector import AutopilotInspectorService
from app.entra.inspector import EntraInspectorService
from app.graph.errors import GraphError, GraphForbiddenError, GraphNotFoundError, GraphThrottledError
from app.graph.models import GraphRequestLog, GraphResponse
from app.intune.device_inspector import IntuneDeviceInspectorService


ENTRA_OBJECT_ID = "22222222-2222-2222-2222-222222222222"
ENTRA_DEVICE_GUID = "33333333-3333-3333-3333-333333333333"
MANAGED_DEVICE_ID = "44444444-4444-4444-4444-444444444444"


def graph_response(data: dict[str, Any], url: str, *, object_count: int | None = None) -> GraphResponse:
    return GraphResponse(data=data, log=GraphRequestLog("GET", url, 200, 10, object_count))


def entra_device_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": ENTRA_OBJECT_ID,
        "deviceId": ENTRA_DEVICE_GUID,
        "displayName": "PC-MRS-0042",
        "accountEnabled": True,
        "operatingSystem": "Windows",
        "operatingSystemVersion": "10.0.26100",
        "trustType": "AzureAd",
        "profileType": "RegisteredDevice",
        "deviceOwnership": "company",
        "enrollmentType": "windowsAzureADJoin",
        "managementType": "mdm",
        "isCompliant": True,
        "isManaged": True,
        "isRooted": False,
        "onPremisesSyncEnabled": None,
        "registrationDateTime": "2025-01-01T00:00:00Z",
        "approximateLastSignInDateTime": "2026-09-10T00:00:00Z",
        "onPremisesLastSyncDateTime": None,
        "complianceExpirationDateTime": None,
    }
    payload.update(overrides)
    return payload


def managed_device_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": MANAGED_DEVICE_ID,
        "deviceName": "PC-MRS-0042",
        "azureADDeviceId": ENTRA_DEVICE_GUID,
        "serialNumber": "SERIAL-001",
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


def autopilot_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": "66666666-6666-6666-6666-666666666666",
        "groupTag": "PROD-MRS",
        "serialNumber": "SERIAL-001",
        "manufacturer": "Dell",
        "model": "Latitude 5450",
        "enrollmentState": "enrolled",
        "lastContactedDateTime": "2026-09-01T00:00:00Z",
        "displayName": "PC-MRS-0042",
        "azureActiveDirectoryDeviceId": ENTRA_DEVICE_GUID,
        "managedDeviceId": MANAGED_DEVICE_ID,
    }
    payload.update(overrides)
    return payload


class EntraFakeGraphClient:
    def __init__(
        self,
        *,
        entra_not_found: bool = False,
        entra_forbidden: bool = False,
        entra_device_overrides: dict[str, Any] | None = None,
        entra_device_id_results: list[dict[str, Any]] | None = None,
        entra_display_name_results: list[dict[str, Any]] | None = None,
        managed_device_overrides: dict[str, Any] | None = None,
        managed_device_not_found: bool = False,
        managed_device_forbidden: bool = False,
        managed_device_error: GraphError | None = None,
        managed_device_bridge_results: list[dict[str, Any]] | None = None,
        name_search_results: list[dict[str, Any]] | None = None,
        autopilot_results: list[dict[str, Any]] | None = None,
        autopilot_forbidden: bool = False,
    ):
        self.entra_not_found = entra_not_found
        self.entra_forbidden = entra_forbidden
        self.entra_device_overrides = entra_device_overrides or {}
        self.entra_device_id_results = entra_device_id_results
        self.entra_display_name_results = entra_display_name_results
        self.managed_device_overrides = managed_device_overrides or {}
        self.managed_device_not_found = managed_device_not_found
        self.managed_device_forbidden = managed_device_forbidden
        self.managed_device_error = managed_device_error
        self.managed_device_bridge_results = managed_device_bridge_results
        self.name_search_results = name_search_results
        self.autopilot_results = autopilot_results
        self.autopilot_forbidden = autopilot_forbidden
        self.calls: list[tuple[str, dict[str, str] | None]] = []

    def get(self, path: str, *, params=None, cancellation=None):  # noqa: ANN001
        self.calls.append((path, params))
        if path == f"devices/{ENTRA_OBJECT_ID}":
            if self.entra_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if self.entra_not_found:
                raise GraphNotFoundError("not found", status_code=404)
            return graph_response(entra_device_payload(**self.entra_device_overrides), path)
        if path.startswith("devices/"):
            raise GraphNotFoundError("not found", status_code=404)
        if path == f"deviceManagement/managedDevices/{MANAGED_DEVICE_ID}":
            if self.managed_device_error:
                raise self.managed_device_error
            if self.managed_device_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if self.managed_device_not_found:
                raise GraphNotFoundError("not found", status_code=404)
            return graph_response(managed_device_payload(**self.managed_device_overrides), path)
        if path.startswith("deviceManagement/managedDevices/"):
            raise GraphNotFoundError("not found", status_code=404)
        raise GraphNotFoundError("not found", status_code=404)

    def get_all(self, path: str, *, params=None, cancellation=None):  # noqa: ANN001
        self.calls.append((path, params))
        filter_value = (params or {}).get("$filter", "")
        if path == "devices":
            if self.entra_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if "deviceId eq" in filter_value:
                values = self.entra_device_id_results if self.entra_device_id_results is not None else [entra_device_payload(**self.entra_device_overrides)]
                return graph_response({"value": values}, path, object_count=len(values))
            if "displayName eq" in filter_value:
                values = self.entra_display_name_results if self.entra_display_name_results is not None else [entra_device_payload(**self.entra_device_overrides)]
                return graph_response({"value": values}, path, object_count=len(values))
            return graph_response({"value": []}, path, object_count=0)
        if path == "deviceManagement/managedDevices":
            if "azureADDeviceId eq" in filter_value and "tolower" not in filter_value:
                if self.managed_device_error:
                    raise self.managed_device_error
                if self.managed_device_forbidden:
                    raise GraphForbiddenError("missing permission", status_code=403)
                if self.managed_device_not_found:
                    return graph_response({"value": []}, path, object_count=0)
                values = (
                    self.managed_device_bridge_results
                    if self.managed_device_bridge_results is not None
                    else [managed_device_payload(**self.managed_device_overrides)]
                )
                return graph_response({"value": values}, path, object_count=len(values))
            if "contains(deviceName" in filter_value:
                values = self.name_search_results if self.name_search_results is not None else []
                return graph_response({"value": values}, path, object_count=len(values))
            if "tolower(serialNumber)" in filter_value:
                match = re.search(r"tolower\(serialNumber\) eq '(.*)'", filter_value)
                queried = match.group(1) if match else ""
                values = [managed_device_payload(**self.managed_device_overrides)] if queried == "serial-001" else []
                return graph_response({"value": values}, path, object_count=len(values))
            return graph_response({"value": []}, path, object_count=0)
        if path == "deviceManagement/windowsAutopilotDeviceIdentities":
            if self.autopilot_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            if self.autopilot_results is not None:
                values = self.autopilot_results
            else:
                match = re.search(r"contains\(serialNumber,'(.*)'\)", filter_value)
                queried = match.group(1) if match else ""
                values = [autopilot_payload()] if queried == "SERIAL-001" else []
            return graph_response({"value": values}, path, object_count=len(values))
        return graph_response({"value": []}, path, object_count=0)


def _build_service(graph: EntraFakeGraphClient) -> EntraInspectorService:
    intune_service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    autopilot_service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    return EntraInspectorService(graph, intune_service, autopilot_service)  # type: ignore[arg-type]


# --- Search ---------------------------------------------------------------


def test_search_by_entra_object_id() -> None:
    graph = EntraFakeGraphClient()
    service = _build_service(graph)
    results, _logs = service.search_devices(ENTRA_OBJECT_ID)
    assert len(results) == 1
    assert results[0].id == ENTRA_OBJECT_ID
    assert graph.calls[0][0] == f"devices/{ENTRA_OBJECT_ID}"


def test_search_by_device_id() -> None:
    graph = EntraFakeGraphClient(entra_not_found=True)  # object-id lookup misses, forces deviceId path
    service = _build_service(graph)
    results, _logs = service.search_devices(ENTRA_DEVICE_GUID)
    assert len(results) == 1
    assert results[0].device_id == ENTRA_DEVICE_GUID


def test_search_by_display_name_unique() -> None:
    graph = EntraFakeGraphClient()
    service = _build_service(graph)
    results, _logs = service.search_devices("PC-MRS-0042")
    assert len(results) == 1
    assert results[0].display_name == "PC-MRS-0042"


def test_search_by_display_name_ambiguous_returns_all() -> None:
    duplicates = [
        entra_device_payload(id="a1"),
        entra_device_payload(id="a2"),
    ]
    graph = EntraFakeGraphClient(entra_display_name_results=duplicates)
    service = _build_service(graph)
    results, _logs = service.search_devices("PC-MRS-0042")
    assert {result.id for result in results} == {"a1", "a2"}


def test_search_device_not_found_returns_empty() -> None:
    graph = EntraFakeGraphClient(entra_display_name_results=[], name_search_results=[])
    service = _build_service(graph)
    results, _logs = service.search_devices("UNKNOWN-NAME")
    assert results == []


def test_search_by_managed_device_id_bridges_to_entra() -> None:
    graph = EntraFakeGraphClient(entra_not_found=True)
    service = _build_service(graph)
    results, _logs = service.search_devices(MANAGED_DEVICE_ID)
    assert len(results) == 1
    assert results[0].device_id == ENTRA_DEVICE_GUID


def test_search_by_serial_via_intune_bridge() -> None:
    graph = EntraFakeGraphClient(entra_display_name_results=[])
    service = _build_service(graph)
    results, _logs = service.search_devices("SERIAL-001")
    assert len(results) == 1
    assert results[0].device_id == ENTRA_DEVICE_GUID


def test_odata_escaping_of_single_quotes() -> None:
    graph = EntraFakeGraphClient()
    service = _build_service(graph)
    service.search_devices("O'Brien-PC")
    name_call = next(call for call in graph.calls if call[0] == "devices" and call[1] and "displayName eq" in call[1].get("$filter", ""))
    assert name_call[1]["$filter"] == "displayName eq 'O''Brien-PC'"


# --- Full inspection --------------------------------------------------------


def test_inspect_device_with_everything_present() -> None:
    graph = EntraFakeGraphClient()
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    health = result.health
    assert health is not None
    assert health.device.account_enabled is True
    assert health.device.is_managed is True
    assert health.intune_device is not None
    assert health.intune_device.device_name == "PC-MRS-0042"
    assert health.autopilot is not None
    assert health.autopilot.serial_number == "SERIAL-001"
    assert health.status == "HEALTHY"
    capability_names = {capability.name for capability in health.capabilities}
    assert {"Entra Device", "Intune Correlation", "Autopilot Correlation"} <= capability_names
    assert all(capability.state == "AVAILABLE" for capability in health.capabilities)


def test_account_enabled_true_creates_no_disabled_issue() -> None:
    graph = EntraFakeGraphClient()
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert not any(issue.id == "entra_device_disabled" for issue in result.health.issues)


def test_account_enabled_false_creates_disabled_issue() -> None:
    graph = EntraFakeGraphClient(entra_device_overrides={"accountEnabled": False})
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert any(issue.id == "entra_device_disabled" and issue.severity == "ERROR" for issue in result.health.issues)


def test_account_enabled_unknown_creates_no_disabled_issue() -> None:
    graph = EntraFakeGraphClient(entra_device_overrides={"accountEnabled": None})
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.device.account_enabled is None
    assert not any(issue.id == "entra_device_disabled" for issue in result.health.issues)


def test_is_managed_true_without_intune_correlation_creates_issue() -> None:
    graph = EntraFakeGraphClient(entra_device_overrides={"isManaged": True}, managed_device_not_found=True)
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.intune_device is None
    assert any(issue.id == "managed_without_intune_correlation" for issue in result.health.issues)


def test_is_managed_unknown_does_not_create_issue_even_without_intune() -> None:
    graph = EntraFakeGraphClient(entra_device_overrides={"isManaged": None}, managed_device_not_found=True)
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.device.is_managed is None
    assert not any(issue.id == "managed_without_intune_correlation" for issue in result.health.issues)


def test_is_managed_false_does_not_create_issue() -> None:
    graph = EntraFakeGraphClient(entra_device_overrides={"isManaged": False}, managed_device_not_found=True)
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert not any(issue.id == "managed_without_intune_correlation" for issue in result.health.issues)


def test_intune_correlation_present() -> None:
    graph = EntraFakeGraphClient()
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.intune_device is not None
    intune_capability = next(c for c in result.health.capabilities if c.name == "Intune Correlation")
    assert intune_capability.state == "AVAILABLE"


def test_intune_correlation_absent_404() -> None:
    graph = EntraFakeGraphClient(managed_device_not_found=True)
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.intune_device is None
    intune_capability = next(c for c in result.health.capabilities if c.name == "Intune Correlation")
    assert intune_capability.state == "AVAILABLE"  # 0 results on a filter is not an error, just "not found"


def test_autopilot_correlation_present() -> None:
    graph = EntraFakeGraphClient()
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.autopilot is not None
    autopilot_capability = next(c for c in result.health.capabilities if c.name == "Autopilot Correlation")
    assert autopilot_capability.state == "AVAILABLE"


def test_autopilot_correlation_absent_when_not_registered() -> None:
    graph = EntraFakeGraphClient(autopilot_results=[])
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.autopilot is None


def test_autopilot_correlation_not_attempted_without_intune_serial() -> None:
    graph = EntraFakeGraphClient(managed_device_not_found=True)
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.autopilot is None
    autopilot_capability = next(c for c in result.health.capabilities if c.name == "Autopilot Correlation")
    assert autopilot_capability.state == "UNAVAILABLE"


# --- Partial failures --------------------------------------------------------


def test_intune_403_does_not_break_inspection() -> None:
    graph = EntraFakeGraphClient(managed_device_forbidden=True)
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    health = result.health
    assert health is not None
    assert health.device.display_name == "PC-MRS-0042"
    assert health.intune_device is None
    intune_capability = next(c for c in health.capabilities if c.name == "Intune Correlation")
    assert intune_capability.state == "PERMISSION_MISSING"


def test_autopilot_403_does_not_break_inspection() -> None:
    graph = EntraFakeGraphClient(autopilot_forbidden=True)
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    health = result.health
    assert health is not None
    assert health.intune_device is not None
    assert health.autopilot is None
    autopilot_capability = next(c for c in health.capabilities if c.name == "Autopilot Correlation")
    assert autopilot_capability.state == "PERMISSION_MISSING"


def test_intune_401_is_partial_failure() -> None:
    from app.graph.errors import GraphAuthenticationError

    graph = EntraFakeGraphClient(managed_device_error=GraphAuthenticationError("bad token", status_code=401))
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.intune_device is None
    intune_capability = next(c for c in result.health.capabilities if c.name == "Intune Correlation")
    assert intune_capability.state == "ERROR"


def test_intune_429_is_partial_failure() -> None:
    graph = EntraFakeGraphClient(managed_device_error=GraphThrottledError("throttled", status_code=429))
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.intune_device is None
    intune_capability = next(c for c in result.health.capabilities if c.name == "Intune Correlation")
    assert intune_capability.state == "ERROR"


def test_intune_5xx_is_partial_failure() -> None:
    graph = EntraFakeGraphClient(managed_device_error=GraphError("server error", status_code=500))
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.intune_device is None
    intune_capability = next(c for c in result.health.capabilities if c.name == "Intune Correlation")
    assert intune_capability.state == "ERROR"


def test_entra_primary_403_propagates() -> None:
    graph = EntraFakeGraphClient(entra_forbidden=True)
    service = _build_service(graph)
    try:
        service.inspect_device(ENTRA_OBJECT_ID)
    except GraphForbiddenError:
        pass
    else:
        raise AssertionError("Expected GraphForbiddenError to propagate")


def test_critical_data_unavailable_when_all_secondary_sources_fail() -> None:
    graph = EntraFakeGraphClient(managed_device_forbidden=True, autopilot_forbidden=True)
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert any(issue.id == "critical_data_unavailable" and issue.severity == "ERROR" for issue in result.health.issues)


# --- Stale sign-in -----------------------------------------------------------


def test_recent_sign_in_is_not_stale() -> None:
    graph = EntraFakeGraphClient()
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert not any(issue.id == "entra_device_stale" for issue in result.health.issues)


def test_old_sign_in_is_stale() -> None:
    graph = EntraFakeGraphClient(entra_device_overrides={"approximateLastSignInDateTime": "2020-01-01T00:00:00Z"})
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert any(issue.id == "entra_device_stale" for issue in result.health.issues)


def test_null_sign_in_date_does_not_crash_or_flag_stale() -> None:
    graph = EntraFakeGraphClient(entra_device_overrides={"approximateLastSignInDateTime": None})
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health is not None
    assert not any(issue.id == "entra_device_stale" for issue in result.health.issues)


# --- Ambiguous Intune correlation --------------------------------------------


def test_ambiguous_intune_correlation_creates_issue_without_picking_arbitrarily() -> None:
    duplicates = [managed_device_payload(id="m1"), managed_device_payload(id="m2")]
    graph = EntraFakeGraphClient(managed_device_bridge_results=duplicates)
    service = _build_service(graph)
    result = service.inspect_device(ENTRA_OBJECT_ID)
    assert result.health.intune_device is None
    assert any(issue.id == "correlation_ambiguous" for issue in result.health.issues)
