from __future__ import annotations

import re
from typing import Any

from app.graph.client import GRAPH_BETA_BASE_URL, CancellationToken, GraphReadOnlyClient
from app.graph.errors import GraphError, GraphNotFoundError
from app.graph.models import GraphRequestLog
from app.intune.health import generate_device_issues, parse_application_status, parse_entra_device
from app.intune.models import (
    Capability,
    ComplianceSummary,
    DeviceHealth,
    DeviceInspectorResult,
    DeviceIssue,
    DeviceSearchResult,
    ManagedDevice,
    SourceStatus,
)


MANAGED_DEVICE_SELECT = ",".join(
    [
        "id",
        "deviceName",
        "azureADDeviceId",
        "serialNumber",
        "manufacturer",
        "model",
        "operatingSystem",
        "osVersion",
        "userPrincipalName",
        "userId",
        "managedDeviceOwnerType",
        "managementAgent",
        "deviceEnrollmentType",
        "complianceState",
        "lastSyncDateTime",
        "enrolledDateTime",
        "deviceCategoryDisplayName",
        "isEncrypted",
        "jailBroken",
    ]
)

ENTRA_DEVICE_SELECT = ",".join(
    [
        "id",
        "deviceId",
        "displayName",
        "accountEnabled",
        "operatingSystem",
        "operatingSystemVersion",
        "trustType",
        "profileType",
        "registrationDateTime",
        "approximateLastSignInDateTime",
    ]
)

UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class IntuneDeviceInspectorService:
    def __init__(self, client: GraphReadOnlyClient, *, stale_device_days: int = 7):
        self.client = client
        self.stale_device_days = stale_device_days

    def search_devices(self, query: str, *, cancellation: CancellationToken | None = None) -> tuple[list[DeviceSearchResult], tuple[GraphRequestLog, ...]]:
        query = query.strip()
        if not query:
            return [], ()
        escaped_query = _odata_string(query)
        lowered_query = _odata_string(query.casefold())
        responses = []
        logs: list[GraphRequestLog] = []
        if UUID_PATTERN.match(query):
            try:
                direct = self.client.get(
                    f"deviceManagement/managedDevices/{query}",
                    params={"$select": MANAGED_DEVICE_SELECT},
                    cancellation=cancellation,
                )
                responses.append(direct.data)
                logs.append(_with_source(direct.log, "Intune device direct lookup"))
            except GraphNotFoundError:
                pass

        search_filters = [f"contains(deviceName,'{escaped_query}')"]
        if UUID_PATTERN.match(query):
            search_filters.append(f"tolower(azureADDeviceId) eq '{lowered_query}'")
        search_filters.append(f"tolower(serialNumber) eq '{lowered_query}'")

        for search_filter in search_filters:
            response = self.client.get_all(
                "deviceManagement/managedDevices",
                params={
                    "$select": MANAGED_DEVICE_SELECT,
                    "$filter": search_filter,
                    "$top": "25",
                },
                cancellation=cancellation,
            )
            responses.extend(response.data.get("value", []))
            logs.extend(_with_source(log, "Intune device search") for log in (response.pages or (response.log,)))
            if responses and search_filter.startswith("contains(deviceName"):
                break

        devices_by_id: dict[str, DeviceSearchResult] = {}
        for item in responses:
            device = _parse_search_result(item)
            if device.id:
                devices_by_id[device.id] = device
        return list(devices_by_id.values()), tuple(logs)

    def inspect_device(self, managed_device_id: str, *, cancellation: CancellationToken | None = None) -> DeviceInspectorResult:
        logs: list[GraphRequestLog] = []
        source_statuses: list[SourceStatus] = []
        raw_sources: dict[str, Any] = {}
        device_response = self.client.get(
            f"deviceManagement/managedDevices/{managed_device_id}",
            params={"$select": MANAGED_DEVICE_SELECT},
            cancellation=cancellation,
        )
        logs.append(_with_source(device_response.log, "Intune managedDevice"))
        raw_sources["Intune Managed Device"] = device_response.data
        source_statuses.append(_source_status("Intune managedDevice", logs[-1], available=True))

        primary_users: tuple[dict[str, Any], ...] = ()
        try:
            users_response = self.client.get_all(
                f"deviceManagement/managedDevices/{managed_device_id}/users",
                params={"$select": "id,displayName,userPrincipalName,mail"},
                cancellation=cancellation,
            )
            user_logs = tuple(_with_source(log, "Primary users") for log in (users_response.pages or (users_response.log,)))
            logs.extend(user_logs)
            primary_users = tuple(dict(item) for item in users_response.data.get("value", []))
            source_statuses.append(_source_status("Primary users", user_logs[-1], available=True))
        except GraphError as exc:
            source_statuses.append(_source_error_status("Primary users", f"deviceManagement/managedDevices/{managed_device_id}/users", exc))
            primary_users = ()
        except Exception as exc:
            source_statuses.append(
                SourceStatus(
                    name="Primary users",
                    available=False,
                    endpoint=f"deviceManagement/managedDevices/{managed_device_id}/users",
                    status_code=None,
                    error=str(exc),
                    api_version="v1.0",
                )
            )
            primary_users = ()

        device = parse_managed_device(
            device_response.data,
            primary_users=primary_users,
            stale_device_days=self.stale_device_days,
        )

        entra_device = None
        if device.entra_device_id:
            source_name = "Entra device"
            endpoint = "devices"
            try:
                entra_response = self.client.get_all(
                    endpoint,
                    params={
                        "$filter": f"deviceId eq '{_odata_string(device.entra_device_id)}'",
                        "$select": ENTRA_DEVICE_SELECT,
                        "$top": "1",
                    },
                    cancellation=cancellation,
                )
                entra_logs = tuple(_with_source(log, source_name) for log in (entra_response.pages or (entra_response.log,)))
                logs.extend(entra_logs)
                values = entra_response.data.get("value", [])
                raw_sources["Entra Device"] = values[0] if len(values) == 1 else {"value": values}
                entra_device = parse_entra_device(values[0]) if len(values) == 1 else None
                source_statuses.append(_source_status(source_name, entra_logs[-1], available=True))
            except GraphError as exc:
                source_statuses.append(_source_error_status(source_name, endpoint, exc))

        applications = ()
        try:
            apps_response = self.client.get_all(
                f"deviceManagement/managedDevices/{managed_device_id}/detectedApps",
                params={"$select": "id,displayName,version,size,publisher,deviceCount"},
                cancellation=cancellation,
            )
            app_logs = tuple(_with_source(log, "Applications") for log in (apps_response.pages or (apps_response.log,)))
            logs.extend(app_logs)
            raw_apps = tuple(dict(item) for item in apps_response.data.get("value", []))
            raw_sources["Applications"] = list(raw_apps)
            applications = tuple(
                parse_application_status({**item, "installState": item.get("installState") or "installed"}, kind="detected_app")
                for item in raw_apps
            )
            source_statuses.append(_source_status("Applications", app_logs[-1], available=True))
        except GraphError as exc:
            raw_sources["Applications"] = {}
            source_statuses.append(_source_error_status("Applications", f"deviceManagement/managedDevices/{managed_device_id}/detectedApps", exc))

        app_failures = self._load_application_failures(managed_device_id, cancellation=cancellation)
        logs.extend(app_failures[1])
        source_statuses.extend(app_failures[2])
        if app_failures[0]:
            applications = tuple({app.id or app.name: app for app in (*applications, *app_failures[0])}.values())
            raw_sources["Application Deployment Status"] = [app.raw for app in app_failures[0]]

        compliance = ComplianceSummary(
            state=device.compliance_state,
            grace_period_expiration_datetime=_optional(device.raw.get("complianceGracePeriodExpirationDateTime")),
            detail="Detailed reason not available through the current Graph endpoint.",
            raw={
                "complianceState": device.compliance_state,
                "complianceGracePeriodExpirationDateTime": device.raw.get("complianceGracePeriodExpirationDateTime"),
            },
        )
        raw_sources["Compliance"] = compliance.raw
        source_statuses.append(
            SourceStatus(
                name="Compliance",
                available=True,
                endpoint="deviceManagement/managedDevices/{id}",
                status_code=device_response.log.status_code,
                duration_ms=0,
                object_count=None,
            )
        )

        health = DeviceHealth(
            intune_device=device,
            entra_device=entra_device,
            applications=applications,
            compliance=compliance,
            sources=tuple(source_statuses),
            capabilities=_build_capabilities(tuple(source_statuses)),
            raw_sources=raw_sources,
        )
        issues = generate_device_issues(health, stale_device_days=self.stale_device_days)
        health = DeviceHealth(**{**health.__dict__, "issues": issues})
        device = ManagedDevice(**{**device.__dict__, "issues": issues})
        return DeviceInspectorResult(device=device, endpoint_logs=tuple(logs), health=health)

    def _load_application_failures(
        self,
        managed_device_id: str,
        *,
        cancellation: CancellationToken | None = None,
    ) -> tuple[tuple[Any, ...], tuple[GraphRequestLog, ...], tuple[SourceStatus, ...]]:
        source_name = "Application failures"
        # This endpoint has no v1.0 equivalent; it is isolated here and its failure
        # (404/403/network) is caught below so a missing beta endpoint never breaks inspection.
        endpoint = f"{GRAPH_BETA_BASE_URL}deviceManagement/mobileAppTroubleshootingEvents"
        try:
            response = self.client.get_all(
                endpoint,
                params={
                    "$filter": f"managedDeviceIdentifier eq '{_odata_string(managed_device_id)}' or deviceId eq '{_odata_string(managed_device_id)}'",
                    "$top": "50",
                },
                cancellation=cancellation,
            )
            logs = tuple(_with_source(log, source_name) for log in (response.pages or (response.log,)))
            apps = tuple(
                parse_application_status({**item, "installState": item.get("installState") or "unknown"}, kind="deployment_status")
                for item in response.data.get("value", [])
            )
            return apps, logs, (_source_status(source_name, logs[-1], available=True),)
        except GraphError as exc:
            return (), (), (_source_error_status(source_name, endpoint, exc),)

    def test_connection(self) -> GraphRequestLog:
        response = self.client.get("deviceManagement/managedDevices", params={"$top": "1", "$select": "id,deviceName"})
        return response.log


def parse_managed_device(
    raw: dict[str, Any],
    *,
    primary_users: tuple[dict[str, Any], ...] = (),
    stale_device_days: int = 7,
) -> ManagedDevice:
    device = ManagedDevice(
        id=str(raw.get("id") or ""),
        device_name=str(raw.get("deviceName") or "Not available"),
        entra_device_id=_optional(raw.get("azureADDeviceId")),
        serial_number=_optional(raw.get("serialNumber")),
        manufacturer=_optional(raw.get("manufacturer")),
        model=_optional(raw.get("model")),
        operating_system=_optional(raw.get("operatingSystem")),
        os_version=_optional(raw.get("osVersion")),
        user_principal_name=_optional(raw.get("userPrincipalName")),
        user_id=_optional(raw.get("userId")),
        owner_type=_optional(raw.get("managedDeviceOwnerType")),
        management_agent=_optional(raw.get("managementAgent")),
        enrollment_type=_optional(raw.get("deviceEnrollmentType")),
        compliance_state=_optional(raw.get("complianceState")),
        last_sync_datetime=_optional(raw.get("lastSyncDateTime")),
        enrolled_datetime=_optional(raw.get("enrolledDateTime")),
        device_category_display_name=_optional(raw.get("deviceCategoryDisplayName")),
        is_encrypted=_optional_bool(raw.get("isEncrypted")),
        is_managed=bool(raw.get("managementAgent") or raw.get("id")),
        jail_broken=_optional(raw.get("jailBroken")),
        raw=dict(raw),
        primary_users=primary_users,
    )
    return ManagedDevice(**{**device.__dict__, "issues": tuple(detect_device_issues(device, stale_device_days=stale_device_days))})


def detect_device_issues(device: ManagedDevice, *, stale_device_days: int = 7) -> list[DeviceIssue]:
    health = DeviceHealth(intune_device=device)
    return list(generate_device_issues(health, stale_device_days=stale_device_days))


def _parse_search_result(raw: dict[str, Any]) -> DeviceSearchResult:
    return DeviceSearchResult(
        id=str(raw.get("id") or ""),
        device_name=str(raw.get("deviceName") or "Not available"),
        serial_number=_optional(raw.get("serialNumber")),
        user_principal_name=_optional(raw.get("userPrincipalName")),
        model=_optional(raw.get("model")),
        operating_system=_optional(raw.get("operatingSystem")),
        compliance_state=_optional(raw.get("complianceState")),
        enrolled_datetime=_optional(raw.get("enrolledDateTime")),
        last_sync_datetime=_optional(raw.get("lastSyncDateTime")),
        raw=dict(raw),
    )


def _with_source(log: GraphRequestLog, source: str) -> GraphRequestLog:
    return GraphRequestLog(
        getattr(log, "method", "GET"),
        log.url,
        log.status_code,
        log.duration_ms,
        getattr(log, "object_count", None),
        source,
        getattr(log, "api_version", "beta" if "/beta/" in log.url else "v1.0"),
        getattr(log, "request_id", None),
        getattr(log, "client_request_id", None),
        getattr(log, "response_date", None),
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
        ("Intune Device", "Device identity", "Intune managedDevice"),
        ("Primary users", "Primary user", "Primary users"),
        ("Entra Device", "Entra correlation", "Entra device"),
        ("Compliance", "Device compliance state", "Compliance"),
        ("Detected Apps", "Detected applications inventory", "Applications"),
        ("Deployment Status", "Application deployment status", "Application failures"),
    ]
    capabilities: list[Capability] = []
    for name, feature, source_name in definitions:
        source = source_by_name.get(source_name)
        if source is None:
            state = "UNAVAILABLE"
            reason = "Source was not queried or no reliable identifier was available."
            required_permission = _required_permission(source_name)
        elif source.permission_missing:
            state = "PERMISSION_MISSING"
            reason = source.error or "Microsoft Graph returned 403."
            required_permission = source.required_permission
        elif not source.available and source.status_code == 404:
            state = "API_UNAVAILABLE"
            reason = source.error or "Microsoft Graph returned 404."
            required_permission = source.required_permission
        elif not source.available:
            state = "ERROR"
            reason = source.error or "Source failed."
            required_permission = source.required_permission
        elif source_name == "Application failures":
            state = "PARTIAL"
            reason = "Deployment status is limited to troubleshooting events returned by Graph."
            required_permission = source.required_permission
        else:
            state = "AVAILABLE"
            reason = None
            required_permission = source.required_permission
        capabilities.append(Capability(name=name, state=state, feature=feature, source=source_name, required_permission=required_permission, reason=reason))
    capabilities.append(
        Capability(
            name="Autopilot",
            state="UNAVAILABLE",
            feature="Autopilot inspection",
            source="Not implemented",
            reason="Not implemented in Phase 3.1",
        )
    )
    return tuple(capabilities)


def _required_permission(source_name: str) -> str | None:
    return {
        "Intune managedDevice": "DeviceManagementManagedDevices.Read.All",
        "Intune device search": "DeviceManagementManagedDevices.Read.All",
        "Intune device direct lookup": "DeviceManagementManagedDevices.Read.All",
        "Primary users": "DeviceManagementManagedDevices.Read.All",
        "Entra device": "Device.Read.All",
        "Applications": "DeviceManagementManagedDevices.Read.All",
        "Application failures": "DeviceManagementManagedDevices.Read.All",
        "Compliance": "DeviceManagementManagedDevices.Read.All",
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
