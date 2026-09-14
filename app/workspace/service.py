from __future__ import annotations

import re
from typing import Any

from app.autopilot.inspector import AutopilotInspectorService
from app.autopilot.models import AutopilotIdentity, AutopilotSearchResult
from app.entra.inspector import EntraInspectorService
from app.entra.models import EntraDeviceDetail
from app.graph.client import CancellationToken
from app.graph.errors import GraphError
from app.graph.models import GraphRequestLog
from app.intune.device_inspector import IntuneDeviceInspectorService
from app.intune.models import Capability, DeviceSearchResult, EntraDevice, ManagedDevice, SourceStatus
from app.workspace.models import (
    AutopilotBlock,
    DeviceWorkspaceResult,
    EntraBlock,
    IdentityConflict,
    IntuneBlock,
    ResolvedIdentity,
    WorkspaceSearchResult,
)


UUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class DeviceWorkspaceService:
    """Pure orchestration layer: no Graph calls of its own beyond one narrow
    Autopilot correlation bridge, no business rules, no new model of truth.
    Every identity/health/issue value comes from the existing Intune,
    Autopilot and Entra services."""

    def __init__(
        self,
        intune_service: IntuneDeviceInspectorService,
        autopilot_service: AutopilotInspectorService,
        entra_service: EntraInspectorService,
    ):
        self.intune_service = intune_service
        self.autopilot_service = autopilot_service
        self.entra_service = entra_service

    def search_devices(
        self, query: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[WorkspaceSearchResult], tuple[GraphRequestLog, ...]]:
        query = query.strip()
        if not query:
            return [], ()
        if UUID_PATTERN.match(query):
            return self._search_guid(query, cancellation=cancellation)
        return self._search_text(query, cancellation=cancellation)

    def inspect(self, candidate: WorkspaceSearchResult, *, cancellation: CancellationToken | None = None) -> DeviceWorkspaceResult:
        if candidate.anchor == "autopilot":
            return self._inspect_from_autopilot(candidate, cancellation=cancellation)
        if candidate.anchor == "entra":
            return self._inspect_from_entra(candidate, cancellation=cancellation)
        return self._inspect_from_intune(candidate, cancellation=cancellation)

    # --- Search -------------------------------------------------------------

    def _search_guid(
        self, query: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[WorkspaceSearchResult], tuple[GraphRequestLog, ...]]:
        logs: list[GraphRequestLog] = []

        intune_results, intune_logs = self.intune_service.search_devices(query, cancellation=cancellation)
        logs.extend(intune_logs)
        if intune_results:
            return [_candidate_from_intune(item) for item in intune_results], tuple(logs)

        autopilot_results, autopilot_logs = self.autopilot_service.search_devices(query, cancellation=cancellation)
        logs.extend(autopilot_logs)
        registered = [item for item in autopilot_results if item.is_registered]
        if registered:
            return [_candidate_from_autopilot(item) for item in registered], tuple(logs)

        entra_results, entra_logs = self.entra_service.search_devices(query, cancellation=cancellation)
        logs.extend(entra_logs)
        if entra_results:
            return [_candidate_from_entra(item) for item in entra_results], tuple(logs)

        return [], tuple(logs)

    def _search_text(
        self, query: str, *, cancellation: CancellationToken | None = None
    ) -> tuple[list[WorkspaceSearchResult], tuple[GraphRequestLog, ...]]:
        logs: list[GraphRequestLog] = []

        # Serial number remains the preferred pivot when Autopilot recognizes it (D022).
        autopilot_results, autopilot_logs = self.autopilot_service.search_devices(query, cancellation=cancellation)
        logs.extend(autopilot_logs)
        registered = [item for item in autopilot_results if item.is_registered]
        if registered:
            return [_candidate_from_autopilot(item) for item in registered], tuple(logs)

        # Not a serial Autopilot recognizes: treat it as a device name via Intune,
        # which finds every matching device regardless of Autopilot registration.
        intune_results, intune_logs = self.intune_service.search_devices(query, cancellation=cancellation)
        logs.extend(intune_logs)
        return [_candidate_from_intune(item) for item in intune_results], tuple(logs)

    # --- Inspection -----------------------------------------------------------

    def _inspect_from_autopilot(
        self, candidate: WorkspaceSearchResult, *, cancellation: CancellationToken | None = None
    ) -> DeviceWorkspaceResult:
        result = self.autopilot_service.inspect_device(
            autopilot_id=candidate.autopilot_id or "",
            fallback_managed_device_id=candidate.managed_device_id,
            fallback_serial_number=candidate.serial_number,
            cancellation=cancellation,
        )
        health = result.health
        identity = health.identity if health else None
        intune_device = health.intune_device if health else None
        entra_device = health.entra_device if health else None
        resolved = _resolve_identity(autopilot_identity=identity, intune_device=intune_device, entra_lightweight=entra_device)
        return DeviceWorkspaceResult(
            query=candidate.label,
            anchor="autopilot",
            resolved_identity=resolved,
            autopilot_block=_autopilot_block_from_identity(identity, health.profile if health else None),
            entra_block=_entra_block_from_lightweight(entra_device),
            intune_block=_intune_block(intune_device),
            issues=health.issues if health else (),
            sources=health.sources if health else (),
            capabilities=health.capabilities if health else (),
            endpoint_logs=result.endpoint_logs,
            raw_sources=dict(health.raw_sources) if health else {},
        )

    def _inspect_from_entra(
        self, candidate: WorkspaceSearchResult, *, cancellation: CancellationToken | None = None
    ) -> DeviceWorkspaceResult:
        result = self.entra_service.inspect_device(candidate.entra_object_id or "", cancellation=cancellation)
        health = result.health
        device = health.device if health else None
        intune_device = health.intune_device if health else None
        autopilot_summary = health.autopilot if health else None
        resolved = _resolve_identity(
            autopilot_summary=autopilot_summary,
            intune_device=intune_device,
            entra_detail=device,
        )
        return DeviceWorkspaceResult(
            query=candidate.label,
            anchor="entra",
            resolved_identity=resolved,
            autopilot_block=_autopilot_block_from_search_result(autopilot_summary),
            entra_block=_entra_block_from_detail(device),
            intune_block=_intune_block(intune_device),
            issues=health.issues if health else (),
            sources=health.sources if health else (),
            capabilities=health.capabilities if health else (),
            endpoint_logs=result.endpoint_logs,
            raw_sources=dict(health.raw_sources) if health else {},
        )

    def _inspect_from_intune(
        self, candidate: WorkspaceSearchResult, *, cancellation: CancellationToken | None = None
    ) -> DeviceWorkspaceResult:
        result = self.intune_service.inspect_device(candidate.managed_device_id or "", cancellation=cancellation)
        health = result.health
        device = result.device
        entra_device = health.entra_device if health else None
        logs = list(result.endpoint_logs)
        sources = list(health.sources) if health else []
        capabilities = list(health.capabilities) if health else []
        raw_sources = dict(health.raw_sources) if health else {}

        # Intune's own inspector has no notion of Autopilot at all, so this is
        # the one bridge call the workspace makes itself - the same lightweight
        # search_devices(serial) bridge Entra's own inspector already uses (D025),
        # not a new pattern. Skipped entirely when there is no serial to query.
        autopilot_summary: AutopilotSearchResult | None = None
        autopilot_block: AutopilotBlock | None = None
        endpoint = "deviceManagement/windowsAutopilotDeviceIdentities"
        if device.serial_number:
            try:
                autopilot_results, autopilot_logs = self.autopilot_service.search_devices(
                    device.serial_number, cancellation=cancellation
                )
                logs.extend(autopilot_logs)
                registered = [item for item in autopilot_results if item.is_registered]
                if autopilot_logs:
                    source_status = _source_status("Autopilot correlation", autopilot_logs[-1], available=True)
                else:
                    source_status = SourceStatus(
                        name="Autopilot correlation",
                        available=True,
                        endpoint=endpoint,
                        status_code=None,
                        object_count=len(registered),
                        required_permission=_required_permission("Autopilot correlation"),
                    )
                sources.append(source_status)
                capabilities.append(
                    _capability_from_source("Autopilot Correlation", "Correlation vers Autopilot", "Autopilot correlation", source_status)
                )
                if len(registered) == 1:
                    autopilot_summary = registered[0]
                    raw_sources["Autopilot"] = autopilot_summary.raw
                    autopilot_block = _autopilot_block_from_search_result(autopilot_summary)
                elif len(registered) == 0:
                    # A successful query with zero registered matches is a confirmed
                    # absence (D023), not an unknown - same principle as Autopilot's
                    # own "not registered" placeholder.
                    autopilot_block = AutopilotBlock(
                        registered=False,
                        serial_number=device.serial_number,
                        group_tag=None,
                        enrollment_state=None,
                        profile_name=None,
                        profile_status=None,
                    )
                # len(registered) > 1: genuinely ambiguous: never guess, leave the block empty.
            except GraphError as exc:
                error_status = _source_error_status("Autopilot correlation", endpoint, exc)
                sources.append(error_status)
                capabilities.append(
                    _capability_from_source("Autopilot Correlation", "Correlation vers Autopilot", "Autopilot correlation", error_status)
                )
        else:
            capabilities.append(
                Capability(
                    name="Autopilot Correlation",
                    state="UNAVAILABLE",
                    feature="Correlation vers Autopilot",
                    source="Autopilot correlation",
                    required_permission=_required_permission("Autopilot correlation"),
                    reason="Aucun numero de serie disponible pour tenter la correlation.",
                )
            )

        resolved = _resolve_identity(autopilot_summary=autopilot_summary, intune_device=device, entra_lightweight=entra_device)
        return DeviceWorkspaceResult(
            query=candidate.label,
            anchor="intune",
            resolved_identity=resolved,
            autopilot_block=autopilot_block,
            entra_block=_entra_block_from_lightweight(entra_device),
            intune_block=_intune_block(device),
            issues=health.issues if health else (),
            sources=tuple(sources),
            capabilities=tuple(capabilities),
            endpoint_logs=tuple(logs),
            raw_sources=raw_sources,
        )


def _candidate_from_intune(result: DeviceSearchResult) -> WorkspaceSearchResult:
    return WorkspaceSearchResult(
        anchor="intune",
        label=result.device_name or "Appareil",
        detail=f"{result.serial_number or 'Non disponible'} · {result.operating_system or 'Non disponible'}",
        managed_device_id=result.id,
        serial_number=result.serial_number,
    )


def _candidate_from_autopilot(result: AutopilotSearchResult) -> WorkspaceSearchResult:
    return WorkspaceSearchResult(
        anchor="autopilot",
        label=result.display_name or result.serial_number or "Appareil",
        detail=f"{result.serial_number or 'Non disponible'} · {result.enrollment_state or 'Non disponible'}",
        autopilot_id=result.id or None,
        managed_device_id=result.managed_device_id,
        serial_number=result.serial_number,
    )


def _candidate_from_entra(result: EntraDeviceDetail) -> WorkspaceSearchResult:
    account_enabled = "Non disponible" if result.account_enabled is None else str(result.account_enabled)
    return WorkspaceSearchResult(
        anchor="entra",
        label=result.display_name or result.device_id or "Appareil",
        detail=f"{result.operating_system or 'Non disponible'} · Compte actif : {account_enabled}",
        entra_object_id=result.id,
    )


def _autopilot_block_from_identity(identity: AutopilotIdentity | None, profile) -> AutopilotBlock | None:
    if identity is None:
        return None
    return AutopilotBlock(
        registered=bool(identity.id),
        serial_number=identity.serial_number,
        group_tag=identity.group_tag,
        enrollment_state=identity.enrollment_state,
        profile_name=profile.display_name if profile else None,
        profile_status=profile.assignment_status if profile else None,
    )


def _autopilot_block_from_search_result(result: AutopilotSearchResult | None) -> AutopilotBlock | None:
    if result is None:
        return None
    return AutopilotBlock(
        registered=result.is_registered,
        serial_number=result.serial_number,
        group_tag=result.group_tag,
        enrollment_state=result.enrollment_state,
        profile_name=None,
        profile_status=None,
    )


def _entra_block_from_detail(detail: EntraDeviceDetail | None) -> EntraBlock | None:
    if detail is None:
        return None
    return EntraBlock(
        account_enabled=detail.account_enabled,
        trust_type=detail.trust_type,
        is_managed=detail.is_managed,
        is_compliant=detail.is_compliant,
        approximate_last_sign_in_datetime=detail.approximate_last_sign_in_datetime,
    )


def _entra_block_from_lightweight(device: EntraDevice | None) -> EntraBlock | None:
    if device is None:
        return None
    return EntraBlock(
        account_enabled=device.account_enabled,
        trust_type=device.trust_type,
        is_managed=None,
        is_compliant=None,
        approximate_last_sign_in_datetime=device.approximate_last_sign_in_datetime,
    )


def _intune_block(device: ManagedDevice | None) -> IntuneBlock | None:
    if device is None:
        return None
    return IntuneBlock(
        compliance_state=device.compliance_state,
        last_sync_datetime=device.last_sync_datetime,
        operating_system=device.operating_system,
        os_version=device.os_version,
        owner_type=device.owner_type,
    )


def _merge_field(field_name: str, candidates: list[tuple[str, str | None]]) -> tuple[str | None, str | None, IdentityConflict | None]:
    provenance: list[tuple[str, str]] = []
    seen: dict[str, str] = {}
    for source, value in candidates:
        if not value:
            continue
        normalized = value.strip().casefold()
        seen.setdefault(normalized, value)
        provenance.append((source, value))
    if not provenance:
        return None, None, None
    winning_source, winning_value = provenance[0]
    if len(seen) == 1:
        return winning_value, winning_source, None
    return winning_value, winning_source, IdentityConflict(field=field_name, values=tuple(provenance))


def _resolve_identity(
    *,
    autopilot_identity: AutopilotIdentity | None = None,
    autopilot_summary: AutopilotSearchResult | None = None,
    intune_device: ManagedDevice | None = None,
    entra_lightweight: EntraDevice | None = None,
    entra_detail: EntraDeviceDetail | None = None,
) -> ResolvedIdentity:
    serial_candidates: list[tuple[str, str | None]] = []
    name_candidates: list[tuple[str, str | None]] = []
    entra_device_id_candidates: list[tuple[str, str | None]] = []

    if autopilot_identity is not None:
        serial_candidates.append(("Autopilot", autopilot_identity.serial_number))
        name_candidates.append(("Autopilot", autopilot_identity.display_name))
        entra_device_id_candidates.append(("Autopilot", autopilot_identity.azure_ad_device_id))
    if autopilot_summary is not None:
        serial_candidates.append(("Autopilot", autopilot_summary.serial_number))
        name_candidates.append(("Autopilot", autopilot_summary.display_name))
    if intune_device is not None:
        serial_candidates.append(("Intune", intune_device.serial_number))
        name_candidates.append(("Intune", intune_device.device_name))
        entra_device_id_candidates.append(("Intune", intune_device.entra_device_id))
    if entra_lightweight is not None:
        name_candidates.append(("Entra", entra_lightweight.display_name))
        entra_device_id_candidates.append(("Entra", entra_lightweight.device_id))
    if entra_detail is not None:
        name_candidates.append(("Entra", entra_detail.display_name))
        entra_device_id_candidates.append(("Entra", entra_detail.device_id))

    serial_value, serial_source, serial_conflict = _merge_field("serial_number", serial_candidates)
    name_value, name_source, name_conflict = _merge_field("device_name", name_candidates)
    entra_device_id_value, entra_device_id_source, entra_device_id_conflict = _merge_field(
        "entra_device_id", entra_device_id_candidates
    )

    sources: dict[str, str] = {}
    if serial_source:
        sources["serial_number"] = serial_source
    if name_source:
        sources["device_name"] = name_source
    if entra_device_id_source:
        sources["entra_device_id"] = entra_device_id_source

    managed_device_id = intune_device.id if intune_device and intune_device.id else None
    if managed_device_id:
        sources["intune_managed_device_id"] = "Intune"

    entra_object_id = entra_detail.id if entra_detail and entra_detail.id else None
    if entra_object_id:
        sources["entra_object_id"] = "Entra"

    autopilot_device_id = None
    if autopilot_identity is not None and autopilot_identity.id:
        autopilot_device_id = autopilot_identity.id
        sources["autopilot_device_id"] = "Autopilot"
    elif autopilot_summary is not None and autopilot_summary.id:
        autopilot_device_id = autopilot_summary.id
        sources["autopilot_device_id"] = "Autopilot"

    conflicts = tuple(conflict for conflict in (serial_conflict, name_conflict, entra_device_id_conflict) if conflict)

    return ResolvedIdentity(
        serial_number=serial_value,
        device_name=name_value,
        intune_managed_device_id=managed_device_id,
        entra_object_id=entra_object_id,
        entra_device_id=entra_device_id_value,
        autopilot_device_id=autopilot_device_id,
        sources=sources,
        conflicts=conflicts,
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


def _capability_from_source(name: str, feature: str, source_name: str, source: SourceStatus) -> Capability:
    if source.permission_missing:
        state = "PERMISSION_MISSING"
        reason = source.error or "Microsoft Graph a renvoye 403."
    elif not source.available and source.status_code == 404:
        state = "API_UNAVAILABLE"
        reason = source.error or "Microsoft Graph a renvoye 404."
    elif not source.available:
        state = "ERROR"
        reason = source.error or "Echec de la source."
    else:
        state = "AVAILABLE"
        reason = None
    return Capability(name=name, state=state, feature=feature, source=source_name, required_permission=source.required_permission, reason=reason)


def _required_permission(source_name: str) -> str | None:
    return {
        "Autopilot correlation": "DeviceManagementServiceConfig.Read.All",
    }.get(source_name)
