from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.entra.models import EntraDeviceDetail, EntraDeviceHealth
from app.intune.models import DeviceIssue
from app.utils.time import parse_graph_datetime


# Entra sign-in staleness measures interactive/token-refresh activity on the
# directory object (approximateLastSignInDateTime), NOT Intune MDM check-in
# activity (managedDevice.lastSyncDateTime, driven by the ~8h Intune sync
# cycle regardless of user interaction). A device can go far longer than an
# Intune check-in interval without a fresh interactive sign-in and still be
# perfectly healthy, so this uses its own, more lenient threshold rather than
# reusing the Intune "stale device" setting from Settings. 90 days matches
# Microsoft's own commonly cited guidance for stale-device sign-in cleanup.
ENTRA_STALE_SIGN_IN_DAYS = 90


def parse_entra_device_detail(raw: dict[str, Any]) -> EntraDeviceDetail:
    return EntraDeviceDetail(
        id=str(raw.get("id") or ""),
        device_id=_optional(raw.get("deviceId")),
        display_name=_optional(raw.get("displayName")),
        account_enabled=_optional_bool(raw.get("accountEnabled")),
        operating_system=_optional(raw.get("operatingSystem")),
        operating_system_version=_optional(raw.get("operatingSystemVersion")),
        trust_type=_optional(raw.get("trustType")),
        profile_type=_optional(raw.get("profileType")),
        device_ownership=_optional(raw.get("deviceOwnership")),
        enrollment_type=_optional(raw.get("enrollmentType")),
        management_type=_optional(raw.get("managementType")),
        is_compliant=_optional_bool(raw.get("isCompliant")),
        is_managed=_optional_bool(raw.get("isManaged")),
        is_rooted=_optional_bool(raw.get("isRooted")),
        on_premises_sync_enabled=_optional_bool(raw.get("onPremisesSyncEnabled")),
        registration_datetime=_optional(raw.get("registrationDateTime")),
        approximate_last_sign_in_datetime=_optional(raw.get("approximateLastSignInDateTime")),
        on_premises_last_sync_datetime=_optional(raw.get("onPremisesLastSyncDateTime")),
        compliance_expiration_datetime=_optional(raw.get("complianceExpirationDateTime")),
        raw=dict(raw),
    )


def generate_entra_issues(
    health: EntraDeviceHealth, *, stale_sign_in_days: int = ENTRA_STALE_SIGN_IN_DAYS
) -> tuple[DeviceIssue, ...]:
    device = health.device
    issues: list[DeviceIssue] = []

    if device.account_enabled is False:
        issues.append(
            DeviceIssue(
                "ERROR",
                "Appareil desactive dans Entra ID",
                "Entra ID indique accountEnabled = false.",
                "Entra device.accountEnabled",
                id="entra_device_disabled",
                evidence="accountEnabled=false",
            )
        )

    if device.approximate_last_sign_in_datetime:
        last_sign_in = parse_graph_datetime(device.approximate_last_sign_in_datetime)
        if last_sign_in:
            age_days = (datetime.now(timezone.utc) - last_sign_in).days
            if age_days > stale_sign_in_days:
                issues.append(
                    DeviceIssue(
                        "WARNING",
                        f"Aucun signe de connexion Entra depuis {age_days} jours",
                        f"Seuil configure : {stale_sign_in_days} jours (approximateLastSignInDateTime, distinct du dernier check-in Intune).",
                        "Entra device.approximateLastSignInDateTime",
                        id="entra_device_stale",
                        evidence=device.approximate_last_sign_in_datetime,
                    )
                )

    intune_source = next((source for source in health.sources if source.name == "Intune managedDevice"), None)
    if intune_source and intune_source.available and intune_source.object_count and intune_source.object_count > 1:
        issues.append(
            DeviceIssue(
                "WARNING",
                "Correlation Intune ambigue",
                "Plusieurs managedDevice Intune correspondent au meme identifiant Entra. Aucun appareil n'a ete choisi automatiquement.",
                "Intune managedDevice.azureADDeviceId",
                id="correlation_ambiguous",
                evidence=f"{intune_source.object_count} matches",
            )
        )
    elif device.is_managed is True and intune_source and intune_source.available and intune_source.object_count == 0:
        issues.append(
            DeviceIssue(
                "WARNING",
                "Appareil annonce gere mais introuvable dans Intune",
                "Entra ID indique isManaged = true, mais aucun managedDevice Intune correspondant n'a ete trouve.",
                "Entra device.isManaged / Intune managedDevice",
                id="managed_without_intune_correlation",
                evidence="isManaged=true",
            )
        )

    secondary_sources = [source for source in health.sources if source.name != "Entra device"]
    if secondary_sources and all(not source.available for source in secondary_sources):
        issues.append(
            DeviceIssue(
                "ERROR",
                "Diagnostic tres limite : les sources secondaires ont echoue",
                "Intune et Autopilot sont indisponibles. Seul l'objet Entra ID de base a pu etre lu.",
                "Entra diagnostic",
                id="critical_data_unavailable",
                evidence=", ".join(source.name for source in secondary_sources),
            )
        )

    return tuple(issues)


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)
