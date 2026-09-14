from __future__ import annotations

import re
from typing import Any

from app.autopilot.inspector import AutopilotInspectorService
from app.entra.health import generate_entra_issues, parse_entra_device_detail
from app.entra.models import EntraDeviceHealth, EntraInspectorResult, EntraSearchResult
from app.graph.client import CancellationToken, GraphReadOnlyClient
from app.graph.errors import GraphError, GraphNotFoundError
from app.graph.models import GraphRequestLog
from app.intune.device_inspector import MANAGED_DEVICE_SELECT, IntuneDeviceInspectorService, _with_source, parse_managed_device
from app.intune.models import Capability, SourceStatus


# alternativeSecurityIds and physicalIds are documented "For internal use
# only" on the v1.0 device resource: no confirmed diagnostic value, and
# fetching/displaying them would be exposure without a clear benefit, so
# they are deliberately not selected here.
ENTRA_DEVICE_DETAIL_SELECT = ",".join(
    [
        "id",
        "deviceId",
        "displayName",
        "accountEnabled",
        "operatingSystem",
        "operatingSystemVersion",
        "trustType",
        "profileType",
        "deviceOwnership",
        "enrollmentType",
        "managementType",
        "isCompliant",
        "isManaged",
        "isRooted",
        "onPremisesSyncEnabled",
        "registrationDateTime",
        "approximateLastSignInDateTime",
        "onPremisesLastSyncDateTime",
        "complianceExpirationDateTime",
    ]
)

UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class EntraInspectorService:
    def __init__(
        self,
        client: GraphReadOnlyClient,
        intune_service: IntuneDeviceInspectorService,
        autopilot_service: AutopilotInspectorService,
        *,
        stale_device_days: int = 7,
    ):
        self.client = client
        self.intune_service = intune_service
        self.autopilot_service = autopilot_service
        self.stale_device_days = stale_device_days

    def search_devices(
        self, query: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[EntraSearchResult], tuple[GraphRequestLog, ...]]:
        query = query.strip()
        if not query:
            return [], ()

        if UUID_PATTERN.match(query):
            direct = self._search_by_object_id(query, cancellation=cancellation)
            if direct is not None:
                return direct
            by_device_id, logs = self._search_by_device_id(query, cancellation=cancellation)
            if by_device_id:
                return by_device_id, logs
            bridged = self._search_by_managed_device_id(query, cancellation=cancellation)
            if bridged is not None and bridged[0]:
                return bridged[0], logs + bridged[1]
            return [], logs

        by_name, logs = self._search_by_display_name(query, cancellation=cancellation)
        if by_name:
            return by_name, logs
        bridged, bridge_logs = self._search_via_intune_bridge(query, cancellation=cancellation)
        return bridged, logs + bridge_logs

    def inspect_device(self, object_id: str, *, cancellation: CancellationToken | None = None) -> EntraInspectorResult:
        logs: list[GraphRequestLog] = []
        source_statuses: list[SourceStatus] = []
        raw_sources: dict[str, Any] = {}

        device_response = self.client.get(
            f"devices/{object_id}", params={"$select": ENTRA_DEVICE_DETAIL_SELECT}, cancellation=cancellation
        )
        logs.append(_with_source(device_response.log, "Entra device"))
        raw_sources["Entra Device"] = device_response.data
        source_statuses.append(_source_status("Entra device", logs[-1], available=True))
        device = parse_entra_device_detail(device_response.data)

        intune_device = None
        if device.device_id:
            endpoint = "deviceManagement/managedDevices"
            try:
                managed_response = self.client.get_all(
                    endpoint,
                    params={
                        "$filter": f"azureADDeviceId eq '{_odata_string(device.device_id)}'",
                        "$select": MANAGED_DEVICE_SELECT,
                        "$top": "2",
                    },
                    cancellation=cancellation,
                )
                managed_logs = tuple(_with_source(log, "Intune managedDevice") for log in (managed_response.pages or (managed_response.log,)))
                logs.extend(managed_logs)
                values = managed_response.data.get("value", [])
                raw_sources["Intune"] = values[0] if len(values) == 1 else {"value": values}
                intune_device = parse_managed_device(values[0], stale_device_days=self.stale_device_days) if len(values) == 1 else None
                source_statuses.append(_source_status("Intune managedDevice", managed_logs[-1], available=True))
            except GraphError as exc:
                source_statuses.append(_source_error_status("Intune managedDevice", endpoint, exc))

        autopilot = None
        if intune_device and intune_device.serial_number:
            endpoint = "deviceManagement/windowsAutopilotDeviceIdentities"
            try:
                autopilot_results, autopilot_logs = self.autopilot_service.search_devices(
                    intune_device.serial_number, cancellation=cancellation
                )
                logs.extend(autopilot_logs)
                registered = [item for item in autopilot_results if item.is_registered]
                if len(registered) == 1:
                    autopilot = registered[0]
                    raw_sources["Autopilot"] = autopilot.raw
                if autopilot_logs:
                    source_statuses.append(_source_status("Autopilot correlation", autopilot_logs[-1], available=True))
                else:
                    source_statuses.append(
                        SourceStatus(
                            name="Autopilot correlation",
                            available=True,
                            endpoint=endpoint,
                            status_code=None,
                            required_permission=_required_permission("Autopilot correlation"),
                        )
                    )
            except GraphError as exc:
                source_statuses.append(_source_error_status("Autopilot correlation", endpoint, exc))

        health = EntraDeviceHealth(
            device=device,
            intune_device=intune_device,
            autopilot=autopilot,
            sources=tuple(source_statuses),
            capabilities=_build_capabilities(tuple(source_statuses)),
            raw_sources=raw_sources,
        )
        issues = generate_entra_issues(health)
        health = EntraDeviceHealth(**{**health.__dict__, "issues": issues})
        return EntraInspectorResult(device=device, endpoint_logs=tuple(logs), health=health)

    def test_connection(self) -> GraphRequestLog:
        response = self.client.get("devices", params={"$top": "1", "$select": "id,displayName"})
        return response.log

    def _search_by_object_id(
        self, object_id: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[EntraSearchResult], tuple[GraphRequestLog, ...]] | None:
        try:
            response = self.client.get(
                f"devices/{object_id}", params={"$select": ENTRA_DEVICE_DETAIL_SELECT}, cancellation=cancellation
            )
        except GraphNotFoundError:
            return None
        log = _with_source(response.log, "Entra device direct lookup")
        return [_parse_search_result(response.data)], (log,)

    def _search_by_device_id(
        self, device_id: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[EntraSearchResult], tuple[GraphRequestLog, ...]]:
        response = self.client.get_all(
            "devices",
            params={"$filter": f"deviceId eq '{_odata_string(device_id)}'", "$select": ENTRA_DEVICE_DETAIL_SELECT, "$top": "25"},
            cancellation=cancellation,
        )
        logs = tuple(_with_source(log, "Entra device search") for log in (response.pages or (response.log,)))
        results = [_parse_search_result(item) for item in response.data.get("value", [])]
        return results, logs

    def _search_by_display_name(
        self, query: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[EntraSearchResult], tuple[GraphRequestLog, ...]]:
        response = self.client.get_all(
            "devices",
            params={"$filter": f"displayName eq '{_odata_string(query)}'", "$select": ENTRA_DEVICE_DETAIL_SELECT, "$top": "25"},
            cancellation=cancellation,
        )
        logs = tuple(_with_source(log, "Entra device search") for log in (response.pages or (response.log,)))
        results = [_parse_search_result(item) for item in response.data.get("value", [])]
        return results, logs

    def _search_by_managed_device_id(
        self, managed_device_id: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[EntraSearchResult], tuple[GraphRequestLog, ...]] | None:
        try:
            response = self.client.get(
                f"deviceManagement/managedDevices/{managed_device_id}",
                params={"$select": "id,azureADDeviceId,deviceName"},
                cancellation=cancellation,
            )
        except GraphError:
            return None
        logs = [_with_source(response.log, "Intune managedDevice lookup")]
        azure_ad_device_id = response.data.get("azureADDeviceId")
        if not azure_ad_device_id:
            return [], tuple(logs)
        results, device_id_logs = self._search_by_device_id(azure_ad_device_id, cancellation=cancellation)
        logs.extend(device_id_logs)
        return results, tuple(logs)

    def _search_via_intune_bridge(
        self, query: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[EntraSearchResult], tuple[GraphRequestLog, ...]]:
        intune_results, intune_logs = self.intune_service.search_devices(query, cancellation=cancellation)
        logs = list(intune_logs)
        results_by_id: dict[str, EntraSearchResult] = {}
        for intune_result in intune_results:
            azure_ad_device_id = intune_result.raw.get("azureADDeviceId")
            if not azure_ad_device_id:
                continue
            found, device_id_logs = self._search_by_device_id(azure_ad_device_id, cancellation=cancellation)
            logs.extend(device_id_logs)
            for item in found:
                results_by_id[item.id] = item
        return list(results_by_id.values()), tuple(logs)


def _parse_search_result(raw: dict[str, Any]) -> EntraSearchResult:
    return EntraSearchResult(
        id=str(raw.get("id") or ""),
        device_id=_optional(raw.get("deviceId")),
        display_name=_optional(raw.get("displayName")),
        operating_system=_optional(raw.get("operatingSystem")),
        account_enabled=_optional_bool(raw.get("accountEnabled")),
        approximate_last_sign_in_datetime=_optional(raw.get("approximateLastSignInDateTime")),
        raw=dict(raw),
    )


def _source_status(name: str, log: GraphRequestLog, *, available: bool) -> SourceStatus:
    return SourceStatus(
        name=name,
        available=available,
        endpoint=log.url,
        status_code=log.status_code,
        duration_ms=log.duration_ms,
        object_count=log.object_count,
        api_version=log.api_version,
        request_id=log.request_id,
        client_request_id=log.client_request_id,
        response_date=log.response_date,
        required_permission=_required_permission(name),
    )


def _source_error_status(name: str, endpoint: str, exc: GraphError) -> SourceStatus:
    return SourceStatus(
        name=name,
        available=False,
        endpoint=endpoint,
        status_code=exc.status_code,
        permission_missing=exc.status_code == 403,
        error=exc.user_message if exc.status_code == 403 else str(exc),
        api_version="v1.0",
        request_id=exc.request_id,
        client_request_id=exc.client_request_id,
        response_date=exc.response_date,
        required_permission=_required_permission(name),
    )


def _build_capabilities(sources: tuple[SourceStatus, ...]) -> tuple[Capability, ...]:
    source_by_name = {source.name: source for source in sources}
    definitions = [
        ("Entra Device", "Identite de l'appareil Entra ID", "Entra device"),
        ("Intune Correlation", "Correlation vers Intune", "Intune managedDevice"),
        ("Autopilot Correlation", "Correlation vers Autopilot", "Autopilot correlation"),
    ]
    capabilities: list[Capability] = []
    for name, feature, source_name in definitions:
        source = source_by_name.get(source_name)
        if source is None:
            state = "UNAVAILABLE"
            reason = "La source n'a pas ete interrogee ou aucun identifiant fiable n'etait disponible."
            required_permission = _required_permission(source_name)
        elif source.permission_missing:
            state = "PERMISSION_MISSING"
            reason = source.error or "Microsoft Graph a renvoye 403."
            required_permission = source.required_permission
        elif not source.available and source.status_code == 404:
            state = "API_UNAVAILABLE"
            reason = source.error or "Microsoft Graph a renvoye 404."
            required_permission = source.required_permission
        elif not source.available:
            state = "ERROR"
            reason = source.error or "Echec de la source."
            required_permission = source.required_permission
        else:
            state = "AVAILABLE"
            reason = None
            required_permission = source.required_permission
        capabilities.append(
            Capability(name=name, state=state, feature=feature, source=source_name, required_permission=required_permission, reason=reason)
        )
    return tuple(capabilities)


def _required_permission(source_name: str) -> str | None:
    return {
        "Entra device": "Device.Read.All",
        "Entra device direct lookup": "Device.Read.All",
        "Entra device search": "Device.Read.All",
        "Intune managedDevice": "DeviceManagementManagedDevices.Read.All",
        "Intune managedDevice lookup": "DeviceManagementManagedDevices.Read.All",
        "Intune device search": "DeviceManagementManagedDevices.Read.All",
        "Autopilot correlation": "DeviceManagementServiceConfig.Read.All",
    }.get(source_name)


def _odata_string(value: str) -> str:
    return value.replace("'", "''")


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)
