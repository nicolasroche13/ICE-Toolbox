from __future__ import annotations

from app.autopilot.inspector import AutopilotInspectorService
from app.entra.inspector import EntraInspectorService
from app.graph.errors import GraphError, GraphForbiddenError, GraphNotFoundError, GraphThrottledError
from app.intune.device_inspector import IntuneDeviceInspectorService
from app.workspace.service import DeviceWorkspaceService
from test_entra import (
    ENTRA_DEVICE_GUID,
    ENTRA_OBJECT_ID,
    MANAGED_DEVICE_ID,
    EntraFakeGraphClient,
    autopilot_payload,
    entra_device_payload,
    graph_response,
    managed_device_payload,
)


AUTOPILOT_ID = "66666666-6666-6666-6666-666666666666"


class WorkspaceFakeGraphClient(EntraFakeGraphClient):
    """Extends the Entra fake with the one endpoint it never needed: a direct
    GET on a specific Autopilot identity by id."""

    def get(self, path, *, params=None, cancellation=None):  # noqa: ANN001
        if path == f"deviceManagement/windowsAutopilotDeviceIdentities/{AUTOPILOT_ID}":
            self.calls.append((path, params))
            if self.autopilot_forbidden:
                raise GraphForbiddenError("missing permission", status_code=403)
            return graph_response(autopilot_payload(), path)
        if path.startswith("deviceManagement/windowsAutopilotDeviceIdentities/"):
            self.calls.append((path, params))
            raise GraphNotFoundError("not found", status_code=404)
        return super().get(path, params=params, cancellation=cancellation)


def _build_workspace(graph) -> DeviceWorkspaceService:
    intune_service = IntuneDeviceInspectorService(graph)  # type: ignore[arg-type]
    autopilot_service = AutopilotInspectorService(graph)  # type: ignore[arg-type]
    entra_service = EntraInspectorService(graph, intune_service, autopilot_service)  # type: ignore[arg-type]
    return DeviceWorkspaceService(intune_service, autopilot_service, entra_service)


# --- Search: one identifier per supported kind ------------------------------


def test_search_by_serial_number() -> None:
    graph = WorkspaceFakeGraphClient()
    service = _build_workspace(graph)
    results, _logs = service.search_devices("SERIAL-001")
    assert len(results) == 1
    assert results[0].serial_number == "SERIAL-001"


def test_search_by_device_name() -> None:
    # autopilot_results=[] forces Autopilot's own name->serial bridge to find
    # nothing, so this isolates "found by name, no Autopilot registration".
    graph = WorkspaceFakeGraphClient(name_search_results=[managed_device_payload()], autopilot_results=[])
    service = _build_workspace(graph)
    results, _logs = service.search_devices("PC-MRS-0042")
    assert len(results) == 1
    assert results[0].anchor == "intune"


def test_search_by_managed_device_id() -> None:
    graph = WorkspaceFakeGraphClient()
    service = _build_workspace(graph)
    results, _logs = service.search_devices(MANAGED_DEVICE_ID)
    assert len(results) == 1
    assert results[0].anchor == "intune"
    assert results[0].managed_device_id == MANAGED_DEVICE_ID


def test_search_by_entra_object_id() -> None:
    graph = WorkspaceFakeGraphClient(entra_device_id_results=[])
    service = _build_workspace(graph)
    results, _logs = service.search_devices(ENTRA_OBJECT_ID)
    assert len(results) == 1
    assert results[0].anchor == "entra"
    assert results[0].entra_object_id == ENTRA_OBJECT_ID


def test_search_by_entra_device_id_resolves_fully() -> None:
    graph = WorkspaceFakeGraphClient()
    service = _build_workspace(graph)
    results, _logs = service.search_devices(ENTRA_DEVICE_GUID)
    assert len(results) == 1  # some anchor resolved it; which one is an implementation detail


def test_search_by_autopilot_device_id() -> None:
    graph = WorkspaceFakeGraphClient()
    service = _build_workspace(graph)
    results, _logs = service.search_devices(AUTOPILOT_ID)
    assert len(results) == 1
    assert results[0].anchor == "autopilot"
    assert results[0].autopilot_id == AUTOPILOT_ID


def test_search_unknown_query_returns_no_results() -> None:
    graph = WorkspaceFakeGraphClient(name_search_results=[], entra_display_name_results=[])
    service = _build_workspace(graph)
    results, _logs = service.search_devices("nothing-matches-this")
    assert results == []


def test_search_ambiguous_name_returns_all_candidates_without_arbitrary_choice() -> None:
    duplicates = [managed_device_payload(id="m1"), managed_device_payload(id="m2")]
    graph = WorkspaceFakeGraphClient(name_search_results=duplicates, autopilot_results=[])
    service = _build_workspace(graph)
    results, _logs = service.search_devices("PC-MRS-0042")
    assert {r.managed_device_id for r in results} == {"m1", "m2"}


# --- Inspection: coverage combinations --------------------------------------


def _candidate_serial(graph) -> object:
    service = _build_workspace(graph)
    results, _ = service.search_devices("SERIAL-001")
    assert len(results) == 1
    return service, results[0]


def test_device_present_everywhere() -> None:
    graph = WorkspaceFakeGraphClient()
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    assert result.resolved_identity.serial_number == "SERIAL-001"
    assert result.resolved_identity.intune_managed_device_id == MANAGED_DEVICE_ID
    assert result.resolved_identity.entra_device_id == ENTRA_DEVICE_GUID
    assert result.resolved_identity.autopilot_device_id
    assert result.autopilot_block is not None and result.autopilot_block.registered is True
    assert result.entra_block is not None
    assert result.intune_block is not None and result.intune_block.compliance_state == "compliant"
    assert result.status == "HEALTHY"


def test_intune_only() -> None:
    graph = WorkspaceFakeGraphClient(
        managed_device_overrides={"azureADDeviceId": None}, autopilot_results=[]
    )
    service = _build_workspace(graph)
    results, _ = service.search_devices(MANAGED_DEVICE_ID)
    result = service.inspect(results[0])
    assert result.intune_block is not None
    assert result.entra_block is None
    assert result.autopilot_block is not None
    assert result.autopilot_block.registered is False


def test_entra_and_intune_no_autopilot() -> None:
    graph = WorkspaceFakeGraphClient(autopilot_results=[])
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    assert result.intune_block is not None
    assert result.entra_block is not None
    assert result.autopilot_block is not None
    assert result.autopilot_block.registered is False


def test_autopilot_and_intune_entra_absent() -> None:
    graph = WorkspaceFakeGraphClient()

    class NoEntraClient(WorkspaceFakeGraphClient):
        def get_all(self, path, *, params=None, cancellation=None):  # noqa: ANN001
            if path == "devices":
                self.calls.append((path, params))
                return graph_response({"value": []}, path, object_count=0)
            return super().get_all(path, params=params, cancellation=cancellation)

    graph = NoEntraClient()
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    assert result.intune_block is not None
    assert result.entra_block is None
    assert result.autopilot_block is not None and result.autopilot_block.registered is True


def test_entra_only() -> None:
    graph = WorkspaceFakeGraphClient(entra_device_id_results=[], managed_device_not_found=True)
    service = _build_workspace(graph)
    results, _ = service.search_devices(ENTRA_OBJECT_ID)
    result = service.inspect(results[0])
    assert result.entra_block is not None
    assert result.intune_block is None
    assert result.autopilot_block is None  # no serial available to even attempt the bridge


def test_non_autopilot_device() -> None:
    graph = WorkspaceFakeGraphClient(name_search_results=[managed_device_payload()], autopilot_results=[])
    service = _build_workspace(graph)
    results, _ = service.search_devices(MANAGED_DEVICE_ID)
    result = service.inspect(results[0])
    assert result.autopilot_block is not None
    assert result.autopilot_block.registered is False
    assert result.intune_block is not None


# --- Partial failures ---------------------------------------------------------


def test_autopilot_bridge_permission_missing_from_intune_anchor() -> None:
    graph = WorkspaceFakeGraphClient(autopilot_forbidden=True)
    service = _build_workspace(graph)
    results, _ = service.search_devices(MANAGED_DEVICE_ID)
    result = service.inspect(results[0])
    assert result.intune_block is not None
    assert result.autopilot_block is None
    capability = next(c for c in result.capabilities if c.name == "Autopilot Correlation")
    assert capability.state == "PERMISSION_MISSING"


def test_autopilot_bridge_429_from_intune_anchor() -> None:
    class ThrottledAutopilotClient(WorkspaceFakeGraphClient):
        def get_all(self, path, *, params=None, cancellation=None):  # noqa: ANN001
            if path == "deviceManagement/windowsAutopilotDeviceIdentities":
                raise GraphThrottledError("throttled", status_code=429)
            return super().get_all(path, params=params, cancellation=cancellation)

    graph = ThrottledAutopilotClient()
    service = _build_workspace(graph)
    results, _ = service.search_devices(MANAGED_DEVICE_ID)
    result = service.inspect(results[0])
    assert result.intune_block is not None
    capability = next(c for c in result.capabilities if c.name == "Autopilot Correlation")
    assert capability.state == "ERROR"


def test_autopilot_bridge_5xx_from_intune_anchor() -> None:
    class BrokenAutopilotClient(WorkspaceFakeGraphClient):
        def get_all(self, path, *, params=None, cancellation=None):  # noqa: ANN001
            if path == "deviceManagement/windowsAutopilotDeviceIdentities":
                raise GraphError("server error", status_code=500)
            return super().get_all(path, params=params, cancellation=cancellation)

    graph = BrokenAutopilotClient()
    service = _build_workspace(graph)
    results, _ = service.search_devices(MANAGED_DEVICE_ID)
    result = service.inspect(results[0])
    assert result.intune_block is not None
    capability = next(c for c in result.capabilities if c.name == "Autopilot Correlation")
    assert capability.state == "ERROR"


def test_entra_permission_missing_from_autopilot_anchor_does_not_break_workspace() -> None:
    graph = WorkspaceFakeGraphClient(entra_forbidden=True)
    service = _build_workspace(graph)
    results, _ = service.search_devices(AUTOPILOT_ID)
    result = service.inspect(results[0])
    assert result.intune_block is not None
    assert result.entra_block is None
    capability = next(c for c in result.capabilities if c.name == "Entra Correlation")
    assert capability.state == "PERMISSION_MISSING"


# --- Identifier conflicts ------------------------------------------------------


def test_identifier_conflict_is_surfaced_not_hidden() -> None:
    graph = WorkspaceFakeGraphClient(managed_device_overrides={"serialNumber": "DIFFERENT-SERIAL"})
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    conflict_fields = {conflict.field for conflict in result.resolved_identity.conflicts}
    assert "serial_number" in conflict_fields
    # The winning value is still surfaced (first source wins), never dropped silently.
    assert result.resolved_identity.serial_number in {"SERIAL-001", "DIFFERENT-SERIAL"}


def test_no_conflict_when_all_sources_agree() -> None:
    graph = WorkspaceFakeGraphClient()
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    assert result.resolved_identity.conflicts == ()


# --- UNKNOWN vs FALSE, consolidation ------------------------------------------


def test_unknown_entra_fields_stay_none_not_false_from_autopilot_anchor() -> None:
    graph = WorkspaceFakeGraphClient()
    service = _build_workspace(graph)
    results, _ = service.search_devices(AUTOPILOT_ID)
    result = service.inspect(results[0])
    # Autopilot's own correlation only ever gives a lightweight Entra view.
    assert result.entra_block is not None
    assert result.entra_block.is_managed is None
    assert result.entra_block.is_compliant is None


def test_consolidated_issues_keep_their_source() -> None:
    graph = WorkspaceFakeGraphClient(entra_device_overrides={"accountEnabled": False})
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    disabled_issues = [issue for issue in result.issues if issue.id == "entra_device_disabled"]
    assert disabled_issues
    assert disabled_issues[0].source == "Entra device.accountEnabled"


def test_consolidated_capabilities_include_all_three_modules() -> None:
    graph = WorkspaceFakeGraphClient()
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    names = {capability.name for capability in result.capabilities}
    assert "Autopilot Identity" in names
    assert "Intune Correlation" in names
    assert "Entra Correlation" in names


def test_status_reflects_worst_severity_across_sources() -> None:
    graph = WorkspaceFakeGraphClient(entra_device_overrides={"accountEnabled": False})
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    assert result.status == "DEGRADED"


# --- Support bundle ------------------------------------------------------------


def test_support_bundle_payload_has_expected_files_and_is_sanitized() -> None:
    from app.workspace.support_bundle import build_workspace_support_bundle_payload

    graph = WorkspaceFakeGraphClient()
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    payload = build_workspace_support_bundle_payload(result)
    assert set(payload) == {
        "identity.json",
        "health.json",
        "capabilities.json",
        "autopilot.json",
        "entra.json",
        "intune.json",
        "diagnostics.json",
    }
    import json

    serialized = json.dumps(payload)
    assert "Bearer" not in serialized
    assert "client_secret" not in serialized.lower() or "[REDACTED]" in serialized


def test_export_workspace_support_bundle_writes_zip_with_all_files(tmp_path) -> None:
    import zipfile

    from app.workspace.support_bundle import export_workspace_support_bundle

    graph = WorkspaceFakeGraphClient()
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    path = export_workspace_support_bundle(result, tmp_path)
    assert path.exists()
    assert path.name.startswith("EndpointToolbox-Appareil-")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
    assert names == {
        "identity.json",
        "health.json",
        "capabilities.json",
        "autopilot.json",
        "entra.json",
        "intune.json",
        "diagnostics.json",
    }


def test_export_workspace_support_bundle_does_not_overwrite(tmp_path) -> None:
    from app.workspace.support_bundle import export_workspace_support_bundle

    graph = WorkspaceFakeGraphClient()
    service, candidate = _candidate_serial(graph)
    result = service.inspect(candidate)
    first = export_workspace_support_bundle(result, tmp_path)
    second = export_workspace_support_bundle(result, tmp_path)
    assert first != second
    assert first.exists() and second.exists()


# --- Refresh (service level: re-inspecting the same candidate) ---------------


def test_refresh_reinspects_with_the_same_identifier() -> None:
    graph = WorkspaceFakeGraphClient()
    service, candidate = _candidate_serial(graph)
    first = service.inspect(candidate)
    second = service.inspect(candidate)
    assert first.resolved_identity == second.resolved_identity
