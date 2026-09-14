from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.autopilot.models import AutopilotSearchResult
from app.intune.models import Capability, DeviceIssue, HealthStatus, ManagedDevice, SourceStatus


@dataclass(frozen=True)
class EntraDeviceDetail:
    id: str
    device_id: str | None
    display_name: str | None
    account_enabled: bool | None
    operating_system: str | None
    operating_system_version: str | None
    trust_type: str | None
    profile_type: str | None
    device_ownership: str | None
    enrollment_type: str | None
    management_type: str | None
    is_compliant: bool | None
    is_managed: bool | None
    is_rooted: bool | None
    on_premises_sync_enabled: bool | None
    registration_datetime: str | None
    approximate_last_sign_in_datetime: str | None
    on_premises_last_sync_datetime: str | None
    compliance_expiration_datetime: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntraSearchResult:
    id: str
    device_id: str | None
    display_name: str | None
    operating_system: str | None
    account_enabled: bool | None
    approximate_last_sign_in_datetime: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EntraDeviceHealth:
    device: EntraDeviceDetail
    intune_device: ManagedDevice | None = None
    autopilot: AutopilotSearchResult | None = None
    issues: tuple[DeviceIssue, ...] = ()
    sources: tuple[SourceStatus, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    raw_sources: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> HealthStatus:
        if not self.device.id:
            return "UNKNOWN"
        severities = {issue.severity for issue in self.issues}
        if "CRITICAL" in severities or "ERROR" in severities:
            return "DEGRADED"
        if "WARNING" in severities:
            return "ATTENTION"
        return "HEALTHY"


@dataclass(frozen=True)
class EntraInspectorResult:
    device: EntraDeviceDetail
    endpoint_logs: tuple[Any, ...]
    health: EntraDeviceHealth | None = None
