from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


IssueSeverity = Literal["INFO", "WARNING", "ERROR", "CRITICAL"]
HealthStatus = Literal["HEALTHY", "ATTENTION", "DEGRADED", "UNKNOWN"]
CapabilityState = Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE", "PERMISSION_MISSING", "API_UNAVAILABLE", "ERROR"]
ApplicationKind = Literal["detected_app", "deployment_status"]


@dataclass(frozen=True)
class DeviceIssue:
    severity: IssueSeverity
    title: str
    reason: str
    source: str
    id: str = ""
    evidence: str = ""

    @property
    def description(self) -> str:
        return self.reason


@dataclass(frozen=True)
class ManagedDevice:
    id: str
    device_name: str
    entra_device_id: str | None
    serial_number: str | None
    manufacturer: str | None
    model: str | None
    operating_system: str | None
    os_version: str | None
    user_principal_name: str | None
    user_id: str | None
    owner_type: str | None
    management_agent: str | None
    enrollment_type: str | None
    compliance_state: str | None
    last_sync_datetime: str | None
    enrolled_datetime: str | None
    device_category_display_name: str | None
    is_encrypted: bool | None
    is_managed: bool
    jail_broken: str | None
    raw: dict[str, Any] = field(default_factory=dict)
    primary_users: tuple[dict[str, Any], ...] = ()
    issues: tuple[DeviceIssue, ...] = ()


@dataclass(frozen=True)
class DeviceSearchResult:
    id: str
    device_name: str
    serial_number: str | None
    user_principal_name: str | None
    model: str | None
    operating_system: str | None
    compliance_state: str | None
    enrolled_datetime: str | None
    last_sync_datetime: str | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class EntraDevice:
    id: str
    device_id: str | None
    display_name: str | None
    account_enabled: bool | None
    operating_system: str | None
    operating_system_version: str | None
    trust_type: str | None
    profile_type: str | None
    registration_datetime: str | None
    approximate_last_sign_in_datetime: str | None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ApplicationStatus:
    id: str
    name: str
    version: str | None
    install_state: str
    kind: ApplicationKind = "detected_app"
    error_code: str | None = None
    last_modified_datetime: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def error_decimal(self) -> int | None:
        if not self.error_code:
            return None
        code = self.error_code.strip()
        try:
            if code.lower().startswith("0x"):
                return int(code, 16)
            return int(code)
        except ValueError:
            return None


@dataclass(frozen=True)
class ComplianceSummary:
    state: str | None
    grace_period_expiration_datetime: str | None = None
    detail: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceStatus:
    name: str
    available: bool
    endpoint: str
    status_code: int | None
    duration_ms: int = 0
    object_count: int | None = None
    permission_missing: bool = False
    error: str | None = None
    api_version: str = "v1.0"
    request_id: str | None = None
    client_request_id: str | None = None
    response_date: str | None = None
    required_permission: str | None = None


@dataclass(frozen=True)
class Capability:
    name: str
    state: CapabilityState
    feature: str
    source: str
    required_permission: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class DeviceHealth:
    intune_device: ManagedDevice
    entra_device: EntraDevice | None = None
    applications: tuple[ApplicationStatus, ...] = ()
    compliance: ComplianceSummary | None = None
    issues: tuple[DeviceIssue, ...] = ()
    sources: tuple[SourceStatus, ...] = ()
    capabilities: tuple[Capability, ...] = ()
    raw_sources: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> HealthStatus:
        if not self.intune_device.id:
            return "UNKNOWN"
        severities = {issue.severity for issue in self.issues}
        if "CRITICAL" in severities:
            return "DEGRADED"
        if "ERROR" in severities:
            return "DEGRADED"
        if "WARNING" in severities:
            return "ATTENTION"
        return "HEALTHY"

    @property
    def failed_applications(self) -> tuple[ApplicationStatus, ...]:
        return tuple(app for app in self.applications if app.kind == "deployment_status" and app.install_state.casefold() == "failed")


@dataclass(frozen=True)
class DeviceInspectorResult:
    device: ManagedDevice
    endpoint_logs: tuple[Any, ...]
    health: DeviceHealth | None = None
