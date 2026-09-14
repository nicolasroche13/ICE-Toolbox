# Permissions Microsoft Graph

Endpoint Toolbox utilise uniquement des permissions Microsoft Graph **Application** read-only.

## Permissions requises

| Feature | Endpoint | Graph API version | Permission Application minimale | Admin consent | Reason |
| --- | --- | --- | --- | --- | --- |
| Settings - Test Connection | `GET /deviceManagement/managedDevices?$top=1&$select=id,deviceName` | v1.0 | `DeviceManagementManagedDevices.Read.All` | Oui | Verifier que l'app peut lire Intune managed devices. |
| Intune Device Search | `GET /deviceManagement/managedDevices` | v1.0 | `DeviceManagementManagedDevices.Read.All` | Oui | Rechercher les postes Intune par nom, serial number et IDs exposes par managedDevice. |
| Intune Device Inspector | `GET /deviceManagement/managedDevices/{managedDeviceId}` | v1.0 | `DeviceManagementManagedDevices.Read.All` | Oui | Lire les proprietes techniques du managed device. |
| Primary users | `GET /deviceManagement/managedDevices/{managedDeviceId}/users` | v1.0 | `DeviceManagementManagedDevices.Read.All` | Oui | Lire les utilisateurs associes au managed device lorsque Graph les retourne. |
| Entra correlation | `GET /devices?$filter=deviceId eq '{azureADDeviceId}'` | v1.0 | `Device.Read.All` | Oui | Confirmer la presence du device dans Entra ID et lire enabled/trust/OS basiques. |
| Device applications detected | `GET /deviceManagement/managedDevices/{managedDeviceId}/detectedApps` | v1.0 | `DeviceManagementManagedDevices.Read.All` | Oui | Lire les applications detectees depuis le point de vue device. |
| Application troubleshooting events | `GET /deviceManagement/mobileAppTroubleshootingEvents` | beta | `DeviceManagementManagedDevices.Read.All` | Oui | Lire les evenements d'installation applicative device-level lorsque disponibles. Endpoint beta utilise avec degradation propre si indisponible. |
| Compliance device-level | champs `complianceState` sur `managedDevice` | v1.0 | `DeviceManagementManagedDevices.Read.All` | Oui | Afficher l'etat de conformite sans details de policy inventes. |
| Autopilot Search / Identity | `GET /deviceManagement/windowsAutopilotDeviceIdentities` et `GET /deviceManagement/windowsAutopilotDeviceIdentities/{id}` | v1.0 | `DeviceManagementServiceConfig.Read.All` | Oui | Rechercher et lire l'identite Autopilot (serial, Group Tag, managedDeviceId, azureActiveDirectoryDeviceId, enrollmentState). |
| Autopilot Profile Assignment | `GET /deviceManagement/windowsAutopilotDeviceIdentities/{id}?$expand=deploymentProfile` | beta (pas d'equivalent v1.0) | `DeviceManagementServiceConfig.Read.All` | Oui | Lire le profil de deploiement reellement assigne et son statut d'assignation. Isole, optionnel, avec repli propre. |

## Sources Microsoft

Documentation Microsoft Graph officielle consultee :

- `List managedDevices` : https://learn.microsoft.com/en-us/graph/api/intune-devices-manageddevice-list?view=graph-rest-1.0
- `Get managedDevice` : https://learn.microsoft.com/en-us/graph/api/intune-devices-manageddevice-get?view=graph-rest-1.0
- `managedDevice resource type` : https://learn.microsoft.com/en-us/graph/api/resources/intune-devices-manageddevice?view=graph-rest-1.0
- `List devices` : https://learn.microsoft.com/en-us/graph/api/device-list?view=graph-rest-1.0
- `List detectedApps` : https://learn.microsoft.com/en-us/graph/api/intune-devices-detectedapp-list?view=graph-rest-1.0
- `Get detectedApp` : https://learn.microsoft.com/en-us/graph/api/intune-devices-detectedapp-get?view=graph-rest-1.0
- `mobileAppTroubleshootingEvent resource type` : https://learn.microsoft.com/en-us/graph/api/resources/intune-troubleshooting-mobileapptroubleshootingevent?view=graph-rest-1.0
- `mobileAppTroubleshootingEvent beta resource type` : https://learn.microsoft.com/en-us/graph/api/resources/intune-troubleshooting-mobileapptroubleshootingevent?view=graph-rest-beta
- `Configure Microsoft Graph API access for Intune` : https://learn.microsoft.com/en-us/intune/developer/configure-graph-api-access
- `List windowsAutopilotDeviceIdentities` : https://learn.microsoft.com/en-us/graph/api/intune-enrollment-windowsautopilotdeviceidentity-list?view=graph-rest-1.0
- `Get windowsAutopilotDeviceIdentity` : https://learn.microsoft.com/en-us/graph/api/intune-enrollment-windowsautopilotdeviceidentity-get?view=graph-rest-1.0
- `windowsAutopilotDeviceIdentity resource type (v1.0)` : https://learn.microsoft.com/en-us/graph/api/resources/intune-enrollment-windowsautopilotdeviceidentity?view=graph-rest-1.0
- `windowsAutopilotDeviceIdentity resource type (beta, deploymentProfile*)` : https://learn.microsoft.com/en-us/graph/api/resources/intune-enrollment-windowsautopilotdeviceidentity?view=graph-rest-beta
- `Get windowsAutopilotDeploymentProfile (beta)` : https://learn.microsoft.com/en-us/graph/api/intune-shared-windowsautopilotdeploymentprofile-get?view=graph-rest-beta
- `windowsAutopilotDeploymentProfile resource type (beta)` : https://learn.microsoft.com/en-us/graph/api/resources/intune-shared-windowsautopilotdeploymentprofile?view=graph-rest-beta

## Hors scope

Permissions explicitement non utilisees :

- `DeviceManagementManagedDevices.ReadWrite.All`
- `Directory.ReadWrite.All`
- `User.ReadWrite.All`
- toute permission `*.ReadWrite.*`

Si une future information necessite une permission plus large, elle doit etre documentee et validee avant implementation.

## Limitations Phase 3

- Les raisons detaillees de non-conformite ne sont pas affichees tant qu'un endpoint stable, minimal et documente n'est pas retenu.
- Les evenements applicatifs detailles utilisent un endpoint beta et peuvent ne pas etre disponibles sur tous les tenants. Endpoint Toolbox degrade alors la section Applications sans erreur globale.
- `DeviceManagementApps.Read.All` n'est pas ajoute automatiquement : Phase 3 ne lit pas les definitions globales d'applications Intune, seulement les donnees device-level retenues ci-dessus.

## Limitations Phase 4 (Autopilot)

- `windowsAutopilotDeviceIdentities` ne supporte fiablement que la fonction `contains()` en `$filter` ; l'operateur `eq` n'est pas supporte par cet endpoint (constat communaute + tests manuels, non documente explicitement par Microsoft). Endpoint Toolbox n'utilise donc que `contains()` pour cette source.
- Un espace brut dans la valeur du filtre peut provoquer un `400 Bad Request` sur cet endpoint. Le numero de serie est normalise (espaces retires) avant d'etre envoye.
- La sensibilite a la casse de `contains()` sur `windowsAutopilotDeviceIdentities` n'est pas confirmee par la documentation officielle ; contrairement a `managedDevices` (Phase 3.1, `tolower()`), aucune fonction de normalisation de casse n'est ajoutee ici tant qu'elle n'est pas confirmee sans risque de casser une recherche qui fonctionne.
- `azureActiveDirectoryDeviceId` sur `windowsAutopilotDeviceIdentity` est documente "to be deprecated" par Microsoft (encore present en v1.0). Endpoint Toolbox privilegie `managedDevice.azureADDeviceId` (Intune) quand il est disponible, et n'utilise le champ Autopilot qu'en repli.
- Le profil de deploiement assigne (`deploymentProfile`, `deploymentProfileAssignmentStatus`, `deploymentProfileAssignmentDetailedStatus`, `deploymentProfileAssignedDateTime`) n'existe qu'en beta : aucun equivalent v1.0 n'est documente pour cette relation depuis un device Autopilot specifique.
- Aucune donnee de groupe d'assignation de profil (`assignments` sur `windowsAutopilotDeploymentProfile`) n'est lue : afficher un profil "potentiellement applicable" via l'appartenance a un groupe serait une deduction, pas une confirmation. Seul le profil reellement assigne au device (`deploymentProfile`) est affiche.
- `_search_by_serial` (utilise en cascade depuis la recherche par nom de poste et par Managed Device ID) ne capture pas les erreurs Graph individuellement : un serial candidat qui provoquerait un statut non 2xx sur `windowsAutopilotDeviceIdentities` interromprait toute la resolution au lieu d'etre simplement ignore. Non corrige tant qu'aucun cas reel ne le confirme necessaire (voir "Validation tenant reel" ci-dessous).
- **Risque de faux positif documente pour `identifier_mismatch`** : la regle compare `identity.azure_ad_device_id` (Autopilot, deprecie) et `managedDevice.azureADDeviceId` (Intune). Un appareil reimage/re-enrole peut obtenir un nouvel objet Entra ID cote Intune sans que le champ deprecie cote Autopilot soit necessairement rafraichi par Microsoft, ce qui produirait une divergence reelle mais non anormale. Non confirme ni infirme sans tenant reel ; a verifier en priorite lors de la premiere validation (voir DECISIONS.md).

## Validation tenant reel

**Statut : non effectuee.** Aucune App Registration n'a encore ete creee cote tenant (au 2026-09-14). Toute la Phase 4 a ete validee uniquement via `tests/test_autopilot.py` et `tests/test_autopilot_support_bundle.py` (client Graph factice) plus une revue statique du code (echappement OData, capture d'erreur generique 4xx/429, chemins de repli beta). Rien ci-dessus n'a ete confirme contre un vrai tenant Microsoft. A refaire des qu'une App Registration avec les 3 permissions et l'Admin Consent est disponible.

## Admin Consent

Comme l'application fonctionne en app-only, un administrateur doit accorder l'Admin Consent sur les permissions Application.
