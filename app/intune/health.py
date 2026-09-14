from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.intune.models import ApplicationStatus, DeviceHealth, DeviceIssue, EntraDevice, ManagedDevice
from app.utils.time import parse_graph_datetime


def generate_device_issues(health: DeviceHealth, *, stale_device_days: int = 7) -> tuple[DeviceIssue, ...]:
    device = health.intune_device
    issues: list[DeviceIssue] = []

    compliance = (device.compliance_state or "").casefold()
    if compliance and compliance not in {"compliant", "unknown"}:
        issues.append(
            DeviceIssue(
                "CRITICAL",
                "Appareil non conforme",
                f"Etat de conformite renvoye par Intune : {device.compliance_state}",
                "Intune managedDevice.complianceState",
                id="intune.non_compliant",
                evidence=str(device.compliance_state),
            )
        )

    stale_issue = _stale_check_in_issue(device, stale_device_days=stale_device_days)
    if stale_issue:
        issues.append(stale_issue)

    entra_status = next((source for source in health.sources if source.name == "Entra device"), None)
    if entra_status and entra_status.available and entra_status.object_count and entra_status.object_count > 1:
        issues.append(
            DeviceIssue(
                "WARNING",
                "Correlation Entra ambigue",
                "Plusieurs appareils Entra correspondent a l'identifiant Azure AD Intune. Aucun appareil n'a ete choisi automatiquement.",
                "Entra device.deviceId",
                id="entra.ambiguous",
                evidence=f"{entra_status.object_count} matches",
            )
        )
    if (
        device.entra_device_id
        and entra_status
        and entra_status.available
        and health.entra_device is None
        and not (entra_status.object_count and entra_status.object_count > 1)
    ):
        issues.append(
            DeviceIssue(
                "WARNING",
                "Appareil Intune trouve mais appareil Entra introuvable",
                "Le managedDevice Intune possede un identifiant Entra, mais aucun appareil correspondant n'a ete renvoye par l'annuaire.",
                "Intune managedDevice.azureADDeviceId / Entra device.deviceId",
                id="entra.not_found",
                evidence=device.entra_device_id,
            )
        )

    if health.entra_device and health.entra_device.account_enabled is False:
        issues.append(
            DeviceIssue(
                "ERROR",
                "Appareil desactive dans Entra ID",
                "Entra ID indique accountEnabled = false.",
                "Entra device.accountEnabled",
                id="entra.disabled",
                evidence="accountEnabled=false",
            )
        )

    if device.is_encrypted is False:
        issues.append(
            DeviceIssue(
                "WARNING",
                "Appareil non chiffre",
                "Intune indique isEncrypted = false.",
                "Intune managedDevice.isEncrypted",
                id="intune.not_encrypted",
                evidence="isEncrypted=false",
            )
        )

    primary_users_status = next((source for source in health.sources if source.name == "Primary users"), None)
    primary_users_known = not health.sources or (primary_users_status is not None and primary_users_status.available)
    if primary_users_known and not device.primary_users and not device.user_principal_name:
        issues.append(
            DeviceIssue(
                "WARNING",
                "Aucun utilisateur principal",
                "Aucun utilisateur principal ni UPN n'a ete renvoye par Graph.",
                "Intune managedDevice.users / userPrincipalName",
                id="intune.no_user",
                evidence="No users returned",
            )
        )

    if not device.serial_number:
        issues.append(
            DeviceIssue(
                "WARNING",
                "Numero de serie manquant",
                "Le numero de serie est absent du managedDevice Intune.",
                "Intune managedDevice.serialNumber",
                id="intune.missing_serial",
                evidence="serialNumber is empty",
            )
        )

    if not device.model or not device.manufacturer:
        issues.append(
            DeviceIssue(
                "INFO",
                "Modele ou fabricant manquant",
                "Le fabricant ou le modele est absent du managedDevice Intune.",
                "Intune managedDevice.manufacturer/model",
                id="intune.missing_hardware",
                evidence=f"manufacturer={device.manufacturer or 'missing'}, model={device.model or 'missing'}",
            )
        )

    if not device.operating_system or not device.os_version:
        issues.append(
            DeviceIssue(
                "WARNING",
                "Informations OS manquantes",
                "Le systeme d'exploitation ou sa version est manquant(e).",
                "Intune managedDevice.operatingSystem/osVersion",
                id="intune.missing_os",
                evidence=f"os={device.operating_system or 'missing'}, version={device.os_version or 'missing'}",
            )
        )

    failed_apps = tuple(
        app for app in health.applications if app.kind == "deployment_status" and app.install_state.casefold() == "failed"
    )
    if failed_apps:
        issues.append(
            DeviceIssue(
                "ERROR",
                "Un ou plusieurs echecs d'installation d'application",
                f"{len(failed_apps)} application(s) signalent un echec d'installation.",
                "Intune application status",
                id="apps.install_failed",
                evidence=", ".join(app.name for app in failed_apps[:5]),
            )
        )

    very_old_issue = _very_old_enrollment_issue(device, stale_device_days=stale_device_days)
    if very_old_issue:
        issues.append(very_old_issue)

    return tuple(_deduplicate_issues(issues))


def _stale_check_in_issue(device: ManagedDevice, *, stale_device_days: int) -> DeviceIssue | None:
    if not device.last_sync_datetime:
        return None
    last_sync = parse_graph_datetime(device.last_sync_datetime)
    if not last_sync:
        return None
    age_days = (datetime.now(timezone.utc) - last_sync).days
    if age_days <= stale_device_days:
        return None
    return DeviceIssue(
        "WARNING",
        f"Dernier check-in il y a {age_days} jours",
        f"Seuil configure : {stale_device_days} jours",
        "Intune managedDevice.lastSyncDateTime",
        id="intune.stale_check_in",
        evidence=device.last_sync_datetime,
    )


def _very_old_enrollment_issue(device: ManagedDevice, *, stale_device_days: int) -> DeviceIssue | None:
    if not device.enrolled_datetime or not device.last_sync_datetime:
        return None
    enrolled = parse_graph_datetime(device.enrolled_datetime)
    last_sync = parse_graph_datetime(device.last_sync_datetime)
    if not enrolled or not last_sync:
        return None
    enrollment_age = (datetime.now(timezone.utc) - enrolled).days
    check_in_age = (datetime.now(timezone.utc) - last_sync).days
    if enrollment_age <= 90 or check_in_age <= max(stale_device_days * 4, 30):
        return None
    return DeviceIssue(
        "WARNING",
        "Inscription tres ancienne sans check-in recent",
        f"Inscrit il y a {enrollment_age} jours, dernier check-in il y a {check_in_age} jours.",
        "Intune managedDevice.enrolledDateTime/lastSyncDateTime",
        id="intune.old_enrollment_stale",
        evidence=f"enrolled={device.enrolled_datetime}, lastSync={device.last_sync_datetime}",
    )


def parse_entra_device(raw: dict[str, Any]) -> EntraDevice:
    return EntraDevice(
        id=str(raw.get("id") or ""),
        device_id=_optional(raw.get("deviceId")),
        display_name=_optional(raw.get("displayName")),
        account_enabled=_optional_bool(raw.get("accountEnabled")),
        operating_system=_optional(raw.get("operatingSystem")),
        operating_system_version=_optional(raw.get("operatingSystemVersion")),
        trust_type=_optional(raw.get("trustType")),
        profile_type=_optional(raw.get("profileType")),
        registration_datetime=_optional(raw.get("registrationDateTime")),
        approximate_last_sign_in_datetime=_optional(raw.get("approximateLastSignInDateTime")),
        raw=dict(raw),
    )


def parse_application_status(raw: dict[str, Any], *, kind: str = "detected_app") -> ApplicationStatus:
    install_state = (
        raw.get("installState")
        or raw.get("status")
        or raw.get("mobileAppInstallStatusValue")
        or raw.get("state")
        or "unknown"
    )
    error_code = (
        raw.get("errorCode")
        or raw.get("hexErrorCode")
        or _nested(raw, "troubleshootingErrorDetails", "hexErrorCode")
        or _nested(raw, "troubleshootingErrorDetails", "errorCode")
    )
    return ApplicationStatus(
        id=str(raw.get("id") or raw.get("applicationId") or raw.get("detectedAppId") or ""),
        name=str(raw.get("displayName") or raw.get("applicationName") or raw.get("name") or "Application inconnue"),
        version=_optional(raw.get("version") or raw.get("displayVersion")),
        install_state=_normalize_install_state(str(install_state)),
        kind="deployment_status" if kind == "deployment_status" else "detected_app",
        error_code=_optional(error_code),
        last_modified_datetime=_optional(raw.get("lastModifiedDateTime") or raw.get("lastStatusUpdateDateTime")),
        raw=dict(raw),
    )


def _normalize_install_state(value: str) -> str:
    text = value.strip() or "unknown"
    lowered = text.casefold()
    if lowered in {"failed", "failure", "error", "installfailed"}:
        return "failed"
    if lowered in {"installed", "success", "completed"}:
        return "installed"
    if lowered in {"pending", "inprogress", "installing", "notinstalled"}:
        return "pending"
    if lowered in {"notapplicable", "not applicable"}:
        return "not_applicable"
    return "unknown" if lowered == "unknown" else text


def _deduplicate_issues(issues: list[DeviceIssue]) -> list[DeviceIssue]:
    seen: set[str] = set()
    result: list[DeviceIssue] = []
    for issue in issues:
        key = issue.id or f"{issue.source}:{issue.title}"
        if key in seen:
            continue
        seen.add(key)
        result.append(issue)
    return result


def _nested(raw: dict[str, Any], *keys: str) -> Any:
    current: Any = raw
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_bool(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)
