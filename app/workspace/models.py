from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.intune.models import Capability, DeviceIssue, HealthStatus, SourceStatus


@dataclass(frozen=True)
class IdentityConflict:
    field: str
    values: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ResolvedIdentity:
    serial_number: str | None = None
    device_name: str | None = None
    intune_managed_device_id: str | None = None
    entra_object_id: str | None = None
    entra_device_id: str | None = None
    autopilot_device_id: str | None = None
    sources: dict[str, str] = field(default_factory=dict)
    conflicts: tuple[IdentityConflict, ...] = ()


@dataclass(frozen=True)
class AutopilotBlock:
    registered: bool | None
    serial_number: str | None
    group_tag: str | None
    enrollment_state: str | None
    profile_name: str | None
    profile_status: str | None


@dataclass(frozen=True)
class EntraBlock:
    account_enabled: bool | None
    trust_type: str | None
    is_managed: bool | None
    is_compliant: bool | None
    approximate_last_sign_in_datetime: str | None


@dataclass(frozen=True)
class IntuneBlock:
    compliance_state: str | None
    last_sync_datetime: str | None
    operating_system: str | None
    os_version: str | None
    owner_type: str | None


@dataclass(frozen=True)
class WorkspaceSearchResult:
    anchor: str
    label: str
    detail: str
    autopilot_id: str | None = None
    managed_device_id: str | None = None
    entra_object_id: str | None = None
    serial_number: str | None = None


@dataclass(frozen=True)
class DeviceWorkspaceResult:
    query: str
    anchor: str
    resolved_identity: ResolvedIdentity
    autopilot_block: AutopilotBlock | None = None
    entra_block: EntraBlock | None = None
    intune_block: IntuneBlock | None = None
    issues: tuple[DeviceIssue, ...] = ()
    sources: tuple[SourceStatus, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    endpoint_logs: tuple[Any, ...] = ()
    raw_sources: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> HealthStatus:
        if not any(
            [
                self.resolved_identity.serial_number,
                self.resolved_identity.device_name,
                self.resolved_identity.intune_managed_device_id,
                self.resolved_identity.entra_object_id,
                self.resolved_identity.autopilot_device_id,
            ]
        ):
            return "UNKNOWN"
        severities = {issue.severity for issue in self.issues}
        if "CRITICAL" in severities or "ERROR" in severities:
            return "DEGRADED"
        if "WARNING" in severities:
            return "ATTENTION"
        return "HEALTHY"
