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

## Admin Consent

Comme l'application fonctionne en app-only, un administrateur doit accorder l'Admin Consent sur les permissions Application.
