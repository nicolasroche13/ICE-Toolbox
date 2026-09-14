# Endpoints Microsoft Graph

Reference technique de chaque endpoint Microsoft Graph appele par Endpoint Toolbox : URL exacte, version, proprietes utilisees, filtres, pagination et limitations. Complementaire de `docs/GRAPH_PERMISSIONS.md` (permissions) et `docs/ARCHITECTURE.md` (usage applicatif).

Toutes les requetes sont GET. Aucun POST/PATCH/PUT/DELETE Graph applicatif n'existe dans le code.

## Intune - managedDevices

| Point | Detail |
| --- | --- |
| Endpoint | `GET /deviceManagement/managedDevices`, `GET /deviceManagement/managedDevices/{id}` |
| Version | v1.0 |
| Pagination | `@odata.nextLink`, gere par `GraphReadOnlyClient.get_all`. |
| Filtres utilises | `contains(deviceName,'...')`, `tolower(serialNumber) eq '...'`, `tolower(azureADDeviceId) eq '...'` (Phase 3.1, D016). |
| Permission | `DeviceManagementManagedDevices.Read.All` (Application). |

## Intune - managedDevices/{id}/users, /detectedApps

Voir `docs/GRAPH_PERMISSIONS.md` ; inchange depuis Phase 3.

## Intune - mobileAppTroubleshootingEvents

| Point | Detail |
| --- | --- |
| Endpoint | `GET /deviceManagement/mobileAppTroubleshootingEvents` |
| Version | beta uniquement (aucun equivalent v1.0 documente). |
| Isolation | Seul appel beta du client Intune, isole dans `_load_application_failures` (`app/intune/device_inspector.py`). |

## Entra ID - devices

| Point | Detail |
| --- | --- |
| Endpoint | `GET /devices` |
| Version | v1.0 |
| Filtre | `$filter=deviceId eq '{azureADDeviceId}'` |
| Permission | `Device.Read.All` (Application). |
| Ambiguite | Si plusieurs devices Entra partagent le meme `deviceId`, aucun n'est choisi automatiquement (`entra.ambiguous` / `correlation_ambiguous`). |

## Autopilot - windowsAutopilotDeviceIdentities (identite)

| Point | Detail |
| --- | --- |
| Endpoint | `GET /deviceManagement/windowsAutopilotDeviceIdentities` (liste), `GET /deviceManagement/windowsAutopilotDeviceIdentities/{id}` (get) |
| Version | **v1.0**. |
| Proprietes utilisees (`$select`) | `id, groupTag, purchaseOrderIdentifier, serialNumber, manufacturer, model, enrollmentState, lastContactedDateTime, userPrincipalName, displayName, azureActiveDirectoryDeviceId, managedDeviceId`. |
| Filtre supporte | `contains(serialNumber,'...')` uniquement. `eq` n'est **pas** fiable sur cet endpoint (retours communaute Microsoft Q&A ; non documente officiellement mais reproductible). |
| Limitation connue | Un espace litteral dans la valeur du filtre peut provoquer un `400 Bad Request`. Endpoint Toolbox retire tous les espaces du numero de serie avant de construire le filtre (`re.sub(r"\s+", "", serial)`). |
| Pagination | `@odata.nextLink` standard. |
| Permission | `DeviceManagementServiceConfig.Read.All` (Application, la moins privilegiee documentee ; aussi valable en `ReadWrite.All` mais jamais demandee). |
| Admin consent | Oui. |
| Source officielle | https://learn.microsoft.com/en-us/graph/api/intune-enrollment-windowsautopilotdeviceidentity-list?view=graph-rest-1.0 |

`enrollmentState` : `unknown`, `enrolled`, `pendingReset`, `failed`, `notContacted` (v1.0 ; `blocked` ajoute en beta). Valeur brute affichee telle quelle (vocabulaire technique Graph conserve en anglais).

`azureActiveDirectoryDeviceId` est documente **"to be deprecated"** par Microsoft. Endpoint Toolbox le lit mais prefere `managedDevice.azureADDeviceId` (Intune, non deprecie) quand disponible pour la correlation Entra (voir D0xx dans `docs/DECISIONS.md`).

## Autopilot - profil de deploiement assigne (beta uniquement)

| Point | Detail |
| --- | --- |
| Endpoint | `GET {beta}/deviceManagement/windowsAutopilotDeviceIdentities/{id}?$expand=deploymentProfile` |
| Version | **beta uniquement**. Aucune version v1.0 de cette relation n'existe (confirme via la documentation Microsoft Learn : la page v1.0 de `windowsAutopilotDeviceIdentity` ne liste aucune relationship ; `deploymentProfile`, `deploymentProfileAssignmentStatus`, `deploymentProfileAssignmentDetailedStatus` et `deploymentProfileAssignedDateTime` n'apparaissent que dans la version beta de la ressource). |
| Proprietes utilisees | `deploymentProfileAssignmentStatus` (`unknown, assignedInSync, assignedOutOfSync, assignedUnkownSyncState, notAssigned, pending, failed`), `deploymentProfileAssignmentDetailedStatus`, `deploymentProfileAssignedDateTime`, et l'objet imbrique `deploymentProfile` (`id, displayName, description, deviceType`). |
| Isolation | Seul appel beta du module Autopilot, dans `AutopilotInspectorService.inspect_device` (`app/autopilot/inspector.py`). Utilise `GRAPH_BETA_BASE_URL` (meme constante que Phase 3.1 pour `mobileAppTroubleshootingEvents`). |
| Repli | Toute erreur (403/404/reseau) sur cet appel ne bloque jamais l'inspection : la capacite `Autopilot Profile` passe a `PERMISSION_MISSING` / `API_UNAVAILABLE` / `ERROR`, le reste du diagnostic (identite, Intune, Entra) continue de s'afficher. |
| Permission | `DeviceManagementServiceConfig.Read.All` (identique a l'identite). |
| Source officielle | https://learn.microsoft.com/en-us/graph/api/intune-shared-windowsautopilotdeploymentprofile-get?view=graph-rest-beta |

Volontairement non lu : la relation `assignments` (groupes cibles) de `windowsAutopilotDeploymentProfile`. Afficher un profil "potentiellement applicable" a partir d'une appartenance a un groupe serait une deduction, pas une confirmation Graph ; seul le profil reellement assigne (`deploymentProfile`) est expose.

## Autopilot - correlation Intune / Entra

Aucun endpoint Autopilot dedie n'est utilise pour la correlation : Endpoint Toolbox reutilise directement les endpoints Intune et Entra deja documentes ci-dessus, a partir des identifiants fiables renvoyes par l'identite Autopilot (`managedDeviceId`, `azureActiveDirectoryDeviceId`) ou par le managedDevice Intune (`azureADDeviceId`).

## Recapitulatif v1.0 / beta

| Endpoint | Version |
| --- | --- |
| managedDevices (liste, get, users, detectedApps) | v1.0 |
| mobileAppTroubleshootingEvents | beta (isole) |
| devices (Entra) | v1.0 |
| windowsAutopilotDeviceIdentities (liste, get) | v1.0 |
| windowsAutopilotDeviceIdentities?$expand=deploymentProfile | beta (isole) |

v1.0 reste prioritaire pour toute nouvelle fonctionnalite. Un appel beta doit rester isole, optionnel, documente ici, et avec repli propre - jamais une dependance silencieuse.
