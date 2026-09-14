from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.autopilot.models import AutopilotDeviceHealth, AutopilotIdentity, AutopilotProfileAssignment
from app.intune.models import DeviceIssue
from app.utils.time import parse_graph_datetime


def parse_autopilot_identity(raw: dict[str, Any]) -> AutopilotIdentity:
    return AutopilotIdentity(
        id=str(raw.get("id") or ""),
        serial_number=_optional(raw.get("serialNumber")),
        group_tag=_optional(raw.get("groupTag")),
        manufacturer=_optional(raw.get("manufacturer")),
        model=_optional(raw.get("model")),
        enrollment_state=_optional(raw.get("enrollmentState")),
        last_contacted_datetime=_optional(raw.get("lastContactedDateTime")),
        managed_device_id=_optional(raw.get("managedDeviceId")),
        azure_ad_device_id=_optional(raw.get("azureActiveDirectoryDeviceId")),
        user_principal_name=_optional(raw.get("userPrincipalName")),
        display_name=_optional(raw.get("displayName")),
        purchase_order_identifier=_optional(raw.get("purchaseOrderIdentifier")),
        raw=dict(raw),
    )


def parse_autopilot_profile(raw: dict[str, Any]) -> AutopilotProfileAssignment | None:
    profile = raw.get("deploymentProfile") or {}
    assignment_status = _optional(raw.get("deploymentProfileAssignmentStatus"))
    assignment_detailed_status = _optional(raw.get("deploymentProfileAssignmentDetailedStatus"))
    assigned_datetime = _optional(raw.get("deploymentProfileAssignedDateTime"))
    if not profile and not assignment_status:
        return None
    return AutopilotProfileAssignment(
        profile_id=_optional(profile.get("id")),
        display_name=_optional(profile.get("displayName")),
        description=_optional(profile.get("description")),
        device_type=_optional(profile.get("deviceType")),
        assignment_status=assignment_status,
        assignment_detailed_status=assignment_detailed_status,
        assigned_datetime=assigned_datetime,
        raw=dict(raw),
    )


def generate_autopilot_issues(health: AutopilotDeviceHealth, *, stale_device_days: int = 7) -> tuple[DeviceIssue, ...]:
    identity = health.identity
    issues: list[DeviceIssue] = []

    if not identity.id and (health.intune_device is not None or identity.serial_number):
        issues.append(
            DeviceIssue(
                "WARNING",
                "Appareil non enregistre dans Autopilot",
                "Aucun enregistrement Windows Autopilot n'a ete trouve pour cet appareil.",
                "Autopilot windowsAutopilotDeviceIdentity",
                id="autopilot_not_registered",
                evidence=identity.serial_number or (health.intune_device.serial_number if health.intune_device else "") or "",
            )
        )

    if health.profile and health.profile.assignment_status:
        status = health.profile.assignment_status.casefold()
        if status == "notassigned":
            issues.append(
                DeviceIssue(
                    "WARNING",
                    "Profil Autopilot non assigne",
                    "Microsoft Graph indique qu'aucun profil de deploiement n'est assigne a cet appareil.",
                    "Autopilot deploymentProfileAssignmentStatus",
                    id="profile_not_assigned",
                    evidence="deploymentProfileAssignmentStatus=notAssigned",
                )
            )
        elif status == "failed":
            detail = health.profile.assignment_detailed_status
            detail_suffix = f" ({detail})" if detail and detail.casefold() != "none" else ""
            issues.append(
                DeviceIssue(
                    "ERROR",
                    "Echec de l'assignation du profil Autopilot",
                    f"Statut d'assignation renvoye par Graph : failed{detail_suffix}",
                    "Autopilot deploymentProfileAssignmentStatus",
                    id="profile_assignment_failed",
                    evidence=f"status=failed, detail={detail or 'none'}",
                )
            )

    intune_source = next((source for source in health.sources if source.name == "Intune managedDevice"), None)
    if identity.managed_device_id and intune_source and not intune_source.available and intune_source.status_code == 404:
        issues.append(
            DeviceIssue(
                "ERROR",
                "Appareil Intune introuvable",
                "Autopilot reference un Managed Device ID qui ne correspond a aucun appareil Intune actuel.",
                "Autopilot managedDeviceId / Intune managedDevice",
                id="intune_device_missing",
                evidence=identity.managed_device_id,
            )
        )
    elif identity.enrollment_state and identity.enrollment_state.casefold() == "enrolled" and not identity.managed_device_id:
        issues.append(
            DeviceIssue(
                "WARNING",
                "Appareil Intune introuvable",
                "Autopilot indique un enrolement mais aucun Managed Device ID n'est associe.",
                "Autopilot enrollmentState / managedDeviceId",
                id="intune_device_missing",
                evidence=f"enrollmentState={identity.enrollment_state}",
            )
        )

    entra_source = next((source for source in health.sources if source.name == "Entra device"), None)
    entra_candidate_id = (health.intune_device.entra_device_id if health.intune_device else None) or identity.azure_ad_device_id
    if entra_source and entra_source.available and entra_source.object_count and entra_source.object_count > 1:
        issues.append(
            DeviceIssue(
                "WARNING",
                "Correlation Entra ambigue",
                "Plusieurs appareils Entra correspondent au meme identifiant. Aucun appareil n'a ete choisi automatiquement.",
                "Entra device.deviceId",
                id="correlation_ambiguous",
                evidence=f"{entra_source.object_count} matches",
            )
        )
    elif (
        entra_candidate_id
        and entra_source
        and entra_source.available
        and health.entra_device is None
    ):
        issues.append(
            DeviceIssue(
                "WARNING",
                "Appareil Entra introuvable",
                "Un identifiant Entra etait disponible mais aucun appareil correspondant n'a ete renvoye par l'annuaire.",
                "Entra device.deviceId",
                id="entra_device_missing",
                evidence=entra_candidate_id,
            )
        )

    if health.entra_device and health.entra_device.account_enabled is False:
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

    if health.intune_device and health.intune_device.last_sync_datetime:
        last_sync = parse_graph_datetime(health.intune_device.last_sync_datetime)
        if last_sync:
            age_days = (datetime.now(timezone.utc) - last_sync).days
            if age_days > stale_device_days:
                issues.append(
                    DeviceIssue(
                        "WARNING",
                        f"Aucune communication Intune depuis {age_days} jours",
                        f"Seuil configure : {stale_device_days} jours",
                        "Intune managedDevice.lastSyncDateTime",
                        id="intune_device_stale",
                        evidence=health.intune_device.last_sync_datetime,
                    )
                )

    if (
        identity.azure_ad_device_id
        and health.intune_device
        and health.intune_device.entra_device_id
        and identity.azure_ad_device_id.casefold() != health.intune_device.entra_device_id.casefold()
    ):
        issues.append(
            DeviceIssue(
                "WARNING",
                "Identifiants Entra incoherents entre Autopilot et Intune",
                "Le device Entra ID enregistre sur l'identite Autopilot ne correspond pas a celui du managedDevice Intune.",
                "Autopilot azureActiveDirectoryDeviceId / Intune managedDevice.azureADDeviceId",
                id="identifier_mismatch",
                evidence=f"autopilot={identity.azure_ad_device_id}, intune={health.intune_device.entra_device_id}",
            )
        )

    secondary_sources = [source for source in health.sources if source.name != "Autopilot identity"]
    if secondary_sources and all(not source.available for source in secondary_sources):
        issues.append(
            DeviceIssue(
                "ERROR",
                "Diagnostic tres limite : la plupart des sources ont echoue",
                "Profil, Intune et Entra ID sont tous indisponibles. Seule l'identite Autopilot de base a pu etre lue.",
                "Autopilot diagnostic",
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
