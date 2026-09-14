from __future__ import annotations

import re
from typing import Any

from app.autopilot.health import generate_autopilot_issues, parse_autopilot_identity, parse_autopilot_profile
from app.autopilot.models import (
    AutopilotDeviceHealth,
    AutopilotIdentity,
    AutopilotInspectorResult,
    AutopilotSearchResult,
)
from app.graph.client import GRAPH_BETA_BASE_URL, CancellationToken, GraphReadOnlyClient
from app.graph.errors import GraphError, GraphNotFoundError
from app.graph.models import GraphRequestLog
from app.intune.device_inspector import (
    ENTRA_DEVICE_SELECT,
    MANAGED_DEVICE_SELECT,
    _with_source,
    parse_managed_device,
)
from app.intune.health import parse_entra_device
from app.intune.models import Capability, SourceStatus


AUTOPILOT_SELECT = ",".join(
    [
        "id",
        "groupTag",
        "purchaseOrderIdentifier",
        "serialNumber",
        "manufacturer",
        "model",
        "enrollmentState",
        "lastContactedDateTime",
        "userPrincipalName",
        "displayName",
        "azureActiveDirectoryDeviceId",
        "managedDeviceId",
    ]
)

UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class AutopilotInspectorService:
    def __init__(self, client: GraphReadOnlyClient, *, stale_device_days: int = 7):
        self.client = client
        self.stale_device_days = stale_device_days

    def search_devices(
        self, query: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[AutopilotSearchResult], tuple[GraphRequestLog, ...]]:
        query = query.strip()
        if not query:
            return [], ()

        if UUID_PATTERN.match(query):
            direct = self._search_by_autopilot_id(query, cancellation=cancellation)
            if direct is not None:
                item, logs = direct
                return [item], logs
            bridged = self._search_by_managed_device_id(query, cancellation=cancellation)
            if bridged is not None:
                return bridged
            bridged = self._search_by_entra_device_id(query, cancellation=cancellation)
            if bridged is not None:
                return bridged
            return [], ()

        results, logs = self._search_by_serial(query, cancellation=cancellation)
        if results:
            return results, logs
        return self._search_by_device_name(query, cancellation=cancellation)

    def inspect_device(
        self,
        *,
        autopilot_id: str = "",
        fallback_managed_device_id: str | None = None,
        fallback_serial_number: str | None = None,
        cancellation: CancellationToken | None = None,
    ) -> AutopilotInspectorResult:
        logs: list[GraphRequestLog] = []
        source_statuses: list[SourceStatus] = []
        raw_sources: dict[str, Any] = {}

        if autopilot_id:
            identity_response = self.client.get(
                f"deviceManagement/windowsAutopilotDeviceIdentities/{autopilot_id}",
                params={"$select": AUTOPILOT_SELECT},
                cancellation=cancellation,
            )
            logs.append(_with_source(identity_response.log, "Autopilot identity"))
            raw_sources["Autopilot"] = identity_response.data
            source_statuses.append(_source_status("Autopilot identity", logs[-1], available=True))
            identity = parse_autopilot_identity(identity_response.data)
        else:
            identity = AutopilotIdentity(
                id="",
                serial_number=_optional(fallback_serial_number),
                group_tag=None,
                manufacturer=None,
                model=None,
                enrollment_state=None,
                last_contacted_datetime=None,
                managed_device_id=_optional(fallback_managed_device_id),
                azure_ad_device_id=None,
                user_principal_name=None,
                display_name=None,
                purchase_order_identifier=None,
                raw={},
            )

        profile = None
        if identity.id:
            # Profile assignment is beta-only (no v1.0 equivalent exists for this relationship).
            # Isolated here; its failure never blocks the rest of the diagnostic.
            profile_endpoint = f"{GRAPH_BETA_BASE_URL}deviceManagement/windowsAutopilotDeviceIdentities/{identity.id}?$expand=deploymentProfile"
            try:
                profile_response = self.client.get(profile_endpoint, cancellation=cancellation)
                profile_log = _with_source(profile_response.log, "Autopilot profile")
                logs.append(profile_log)
                raw_sources["Autopilot Profile"] = profile_response.data
                source_statuses.append(_source_status("Autopilot profile", profile_log, available=True))
                profile = parse_autopilot_profile(profile_response.data)
            except GraphError as exc:
                source_statuses.append(_source_error_status("Autopilot profile", profile_endpoint, exc))

        intune_device = None
        managed_device_id = identity.managed_device_id or fallback_managed_device_id
        if managed_device_id:
            endpoint = f"deviceManagement/managedDevices/{managed_device_id}"
            try:
                managed_response = self.client.get(endpoint, params={"$select": MANAGED_DEVICE_SELECT}, cancellation=cancellation)
                managed_log = _with_source(managed_response.log, "Intune managedDevice")
                logs.append(managed_log)
                raw_sources["Intune"] = managed_response.data
                source_statuses.append(_source_status("Intune managedDevice", managed_log, available=True))
                intune_device = parse_managed_device(managed_response.data, stale_device_days=self.stale_device_days)
            except GraphError as exc:
                source_statuses.append(_source_error_status("Intune managedDevice", endpoint, exc))

        entra_device = None
        # Prefer the non-deprecated Intune azureADDeviceId over the Autopilot
        # identity's own azureActiveDirectoryDeviceId ("to be deprecated" per Graph docs).
        entra_id_value = (intune_device.entra_device_id if intune_device else None) or identity.azure_ad_device_id
        if entra_id_value:
            endpoint = "devices"
            try:
                entra_response = self.client.get_all(
                    endpoint,
                    params={
                        "$filter": f"deviceId eq '{_odata_string(entra_id_value)}'",
                        "$select": ENTRA_DEVICE_SELECT,
                        "$top": "2",
                    },
                    cancellation=cancellation,
                )
                entra_logs = tuple(_with_source(log, "Entra device") for log in (entra_response.pages or (entra_response.log,)))
                logs.extend(entra_logs)
                values = entra_response.data.get("value", [])
                raw_sources["Entra"] = values[0] if len(values) == 1 else {"value": values}
                entra_device = parse_entra_device(values[0]) if len(values) == 1 else None
                source_statuses.append(_source_status("Entra device", entra_logs[-1], available=True))
            except GraphError as exc:
                source_statuses.append(_source_error_status("Entra device", endpoint, exc))

        health = AutopilotDeviceHealth(
            identity=identity,
            profile=profile,
            intune_device=intune_device,
            entra_device=entra_device,
            sources=tuple(source_statuses),
            capabilities=_build_capabilities(tuple(source_statuses)),
            raw_sources=raw_sources,
        )
        issues = generate_autopilot_issues(health, stale_device_days=self.stale_device_days)
        health = AutopilotDeviceHealth(**{**health.__dict__, "issues": issues})
        return AutopilotInspectorResult(identity=identity, endpoint_logs=tuple(logs), health=health)

    def test_connection(self) -> GraphRequestLog:
        response = self.client.get(
            "deviceManagement/windowsAutopilotDeviceIdentities", params={"$top": "1", "$select": "id,serialNumber"}
        )
        return response.log

    def _search_by_autopilot_id(
        self, autopilot_id: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[AutopilotSearchResult, tuple[GraphRequestLog, ...]] | None:
        try:
            response = self.client.get(
                f"deviceManagement/windowsAutopilotDeviceIdentities/{autopilot_id}",
                params={"$select": AUTOPILOT_SELECT},
                cancellation=cancellation,
            )
        except GraphNotFoundError:
            return None
        log = _with_source(response.log, "Autopilot direct lookup")
        return _parse_search_result(response.data), (log,)

    def _search_by_managed_device_id(
        self, managed_device_id: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[AutopilotSearchResult], tuple[GraphRequestLog, ...]] | None:
        try:
            response = self.client.get(
                f"deviceManagement/managedDevices/{managed_device_id}",
                params={"$select": "id,serialNumber,deviceName"},
                cancellation=cancellation,
            )
        except GraphError:
            return None
        logs = [_with_source(response.log, "Intune managedDevice lookup")]
        serial = response.data.get("serialNumber")
        if not serial:
            return [], tuple(logs)
        results, serial_logs = self._search_by_serial(serial, cancellation=cancellation)
        logs.extend(serial_logs)
        if not results:
            results = [
                AutopilotSearchResult(
                    id="",
                    serial_number=_optional(serial),
                    display_name=_optional(response.data.get("deviceName")),
                    group_tag=None,
                    enrollment_state=None,
                    manufacturer=None,
                    model=None,
                    last_contacted_datetime=None,
                    managed_device_id=_optional(response.data.get("id")),
                    raw={},
                )
            ]
        return results, tuple(logs)

    def _search_by_entra_device_id(
        self, entra_device_id: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[AutopilotSearchResult], tuple[GraphRequestLog, ...]] | None:
        try:
            entra_response = self.client.get_all(
                "devices",
                params={"$filter": f"deviceId eq '{_odata_string(entra_device_id)}'", "$select": "id,deviceId", "$top": "2"},
                cancellation=cancellation,
            )
        except GraphError:
            return None
        logs = [_with_source(log, "Entra device lookup") for log in (entra_response.pages or (entra_response.log,))]
        if len(entra_response.data.get("value", [])) != 1:
            return [], tuple(logs)
        try:
            managed_response = self.client.get_all(
                "deviceManagement/managedDevices",
                params={
                    "$filter": f"azureADDeviceId eq '{_odata_string(entra_device_id)}'",
                    "$select": "id,serialNumber,deviceName",
                    "$top": "2",
                },
                cancellation=cancellation,
            )
        except GraphError:
            return [], tuple(logs)
        logs.extend(_with_source(log, "Intune device search") for log in (managed_response.pages or (managed_response.log,)))
        managed_values = managed_response.data.get("value", [])
        if len(managed_values) != 1 or not managed_values[0].get("serialNumber"):
            return [], tuple(logs)
        results, serial_logs = self._search_by_serial(managed_values[0]["serialNumber"], cancellation=cancellation)
        logs.extend(serial_logs)
        return results, tuple(logs)

    def _search_by_serial(
        self, serial: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[AutopilotSearchResult], tuple[GraphRequestLog, ...]]:
        # windowsAutopilotDeviceIdentities only reliably supports contains() and
        # rejects raw spaces in the filter value, so we strip whitespace defensively.
        normalized = re.sub(r"\s+", "", serial or "")
        if not normalized:
            return [], ()
        response = self.client.get_all(
            "deviceManagement/windowsAutopilotDeviceIdentities",
            params={"$filter": f"contains(serialNumber,'{_odata_string(normalized)}')", "$select": AUTOPILOT_SELECT, "$top": "25"},
            cancellation=cancellation,
        )
        logs = tuple(_with_source(log, "Autopilot search") for log in (response.pages or (response.log,)))
        results = [_parse_search_result(item) for item in response.data.get("value", [])]
        return results, logs

    def _search_by_device_name(
        self, query: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[AutopilotSearchResult], tuple[GraphRequestLog, ...]]:
        response = self.client.get_all(
            "deviceManagement/managedDevices",
            params={"$filter": f"contains(deviceName,'{_odata_string(query)}')", "$select": "id,serialNumber,deviceName", "$top": "25"},
            cancellation=cancellation,
        )
        logs = list(_with_source(log, "Intune device search") for log in (response.pages or (response.log,)))
        serials = {item.get("serialNumber") for item in response.data.get("value", []) if item.get("serialNumber")}
        results_by_key: dict[str, AutopilotSearchResult] = {}
        for serial in serials:
            found, serial_logs = self._search_by_serial(serial, cancellation=cancellation)
            logs.extend(serial_logs)
            for item in found:
                key = item.id or f"unregistered:{item.serial_number}"
                results_by_key[key] = item
        return list(results_by_key.values()), tuple(logs)


def _parse_search_result(raw: dict[str, Any]) -> AutopilotSearchResult:
    return AutopilotSearchResult(
        id=str(raw.get("id") or ""),
        serial_number=_optional(raw.get("serialNumber")),
        display_name=_optional(raw.get("displayName")),
        group_tag=_optional(raw.get("groupTag")),
        enrollment_state=_optional(raw.get("enrollmentState")),
        manufacturer=_optional(raw.get("manufacturer")),
        model=_optional(raw.get("model")),
        last_contacted_datetime=_optional(raw.get("lastContactedDateTime")),
        managed_device_id=_optional(raw.get("managedDeviceId")),
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
        api_version="beta" if "/beta/" in endpoint else "v1.0",
        request_id=exc.request_id,
        client_request_id=exc.client_request_id,
        response_date=exc.response_date,
        required_permission=_required_permission(name),
    )


def _build_capabilities(sources: tuple[SourceStatus, ...]) -> tuple[Capability, ...]:
    source_by_name = {source.name: source for source in sources}
    definitions = [
        ("Autopilot Identity", "Identite de l'appareil Autopilot", "Autopilot identity"),
        ("Enrollment Information", "Informations d'enrolement Autopilot", "Autopilot identity"),
        ("Autopilot Profile", "Profil de deploiement assigne", "Autopilot profile"),
        ("Intune Correlation", "Correlation vers Intune", "Intune managedDevice"),
        ("Entra Correlation", "Correlation vers Entra ID", "Entra device"),
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
        "Autopilot identity": "DeviceManagementServiceConfig.Read.All",
        "Autopilot search": "DeviceManagementServiceConfig.Read.All",
        "Autopilot direct lookup": "DeviceManagementServiceConfig.Read.All",
        "Autopilot profile": "DeviceManagementServiceConfig.Read.All",
        "Intune managedDevice": "DeviceManagementManagedDevices.Read.All",
        "Intune managedDevice lookup": "DeviceManagementManagedDevices.Read.All",
        "Intune device search": "DeviceManagementManagedDevices.Read.All",
        "Entra device": "Device.Read.All",
        "Entra device lookup": "Device.Read.All",
    }.get(source_name)


def _odata_string(value: str) -> str:
    return value.replace("'", "''")


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
