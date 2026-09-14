from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.intune.models import Capability, DeviceIssue, EntraDevice, HealthStatus, ManagedDevice, SourceStatus


@dataclass(frozen=True)
class AutopilotIdentity:
    id: str
    serial_number: str | None
    group_tag: str | None
    manufacturer: str | None
    model: str | None
    enrollment_state: str | None
    last_contacted_datetime: str | None
    managed_device_id: str | None
    azure_ad_device_id: str | None
    user_principal_name: str | None
    display_name: str | None
    purchase_order_identifier: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AutopilotProfileAssignment:
    profile_id: str | None
    display_name: str | None
    description: str | None
    device_type: str | None
    assignment_status: str | None
    assignment_detailed_status: str | None
    assigned_datetime: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AutopilotSearchResult:
    id: str
    serial_number: str | None
    display_name: str | None
    group_tag: str | None
    enrollment_state: str | None
    manufacturer: str | None
    model: str | None
    last_contacted_datetime: str | None
    managed_device_id: str | None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_registered(self) -> bool:
        return bool(self.id)


@dataclass(frozen=True)
class AutopilotDeviceHealth:
    identity: AutopilotIdentity
    profile: AutopilotProfileAssignment | None = None
    intune_device: ManagedDevice | None = None
    entra_device: EntraDevice | None = None
    issues: tuple[DeviceIssue, ...] = ()
    sources: tuple[SourceStatus, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    raw_sources: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> HealthStatus:
        if not self.identity.id and not self.intune_device:
            return "UNKNOWN"
        severities = {issue.severity for issue in self.issues}
        if "CRITICAL" in severities or "ERROR" in severities:
            return "DEGRADED"
        if "WARNING" in severities:
            return "ATTENTION"
        return "HEALTHY"


@dataclass(frozen=True)
class AutopilotInspectorResult:
    identity: AutopilotIdentity
    endpoint_logs: tuple[Any, ...]
    health: AutopilotDeviceHealth | None = None
