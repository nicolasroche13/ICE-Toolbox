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
| Entra Device Detail | `GET /devices/{id}` et `GET /devices?$filter=deviceId eq '...' ou displayName eq '...'` | v1.0 | `Device.Read.All` | Oui (deja accorde depuis Phase 3) | Rechercher et lire l'identite Entra ID complete (accountEnabled, isCompliant, isManaged, trustType, dates) pour la page Entra ID (Phase 5). **Aucune permission supplementaire : reutilise `Device.Read.All` deja documente.** |

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
- `device resource type (v1.0)` : https://learn.microsoft.com/en-us/graph/api/resources/device?view=graph-rest-1.0
- `Get device` : https://learn.microsoft.com/en-us/graph/api/device-get?view=graph-rest-1.0

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
- **Trouve en concevant Phase 6** : `_search_by_device_name` (recherche par nom de poste, bascule interne d'`AutopilotInspectorService.search_devices`) ignore silencieusement tout appareil Intune trouve par nom qui n'a aucun enregistrement Autopilot correspondant - contrairement a `_search_by_managed_device_id`/`_search_by_entra_device_id` qui synthetisent explicitement un resultat "non enregistre" (D023). Un appel direct a `AutopilotInspectorService.search_devices("nom du poste")` peut donc renvoyer une liste vide meme si l'appareil existe reellement dans Intune. Le Workspace (Phase 6) contourne cette limitation en interrogeant `IntuneDeviceInspectorService.search_devices` directement pour toute recherche par nom, plutot que de se fier uniquement au pont interne d'Autopilot. Non corrige dans `app/autopilot/inspector.py` lui-meme (comportement pre-existant, hors necessite directe de cette phase).

## Limitations Phase 5 (Entra ID)

- La recherche par `displayName` est une egalite exacte (`eq`), pas une recherche partielle : `contains` n'est pas documente comme supporte sur cette propriete pour la ressource `device`. Un nom saisi partiellement ou avec une casse differente ne trouvera rien ; repli automatique sur la recherche Intune (`contains(deviceName, ...)`) qui, elle, est une recherche partielle.
- Aucune fonction `tolower()` n'est appliquee sur les filtres `devices` (contrairement a `managedDevices`, D016) : non confirme sans risque sur cette ressource, a valider sur tenant reel avant d'envisager de l'ajouter.
- `alternativeSecurityIds` et `physicalIds` ne sont deliberement jamais lus ni affiches (documentes "for internal use only" par Microsoft, sans valeur diagnostique confirmee).
- La correlation Autopilot depuis la page Entra ID est une correlation legere (identite de base uniquement, via `AutopilotInspectorService.search_devices`) : elle n'appelle jamais l'endpoint beta du profil de deploiement, pour ne pas dupliquer un appel beta non demande par cette page. Pour voir le profil complet, utiliser la page Autopilot.
- Si plusieurs enregistrements Autopilot partagent le meme numero de serie resolu depuis Intune, la correlation Autopilot de la page Entra reste `None` (pas de choix arbitraire) sans lever d'issue dediee - deja couvert par les regles de Phase 4 si l'utilisateur va verifier directement sur la page Autopilot.

## Limitations Phase 6 (Device Workspace)

- **Aucune permission ni endpoint supplementaire.** Le Workspace est une couche d'orchestration ; il reutilise integralement les appels deja documentes ci-dessus.
- La resolution d'un GUID ambigu (Managed Device ID vs Autopilot ID vs Entra Object ID vs Entra deviceId) essaie Intune puis Autopilot puis Entra dans cet ordre fixe ; dans le pire cas (un Entra Object ID que ni Intune ni Autopilot ne reconnaissent), cela peut declencher jusqu'a une demi-douzaine d'appels Graph avant d'aboutir a Entra. Chaque appel individuel reutilise le comportement deja teste de son module d'origine ; aucun n'est duplique ou reimplemente, mais le nombre total d'appels pour ce cas precis n'est pas minimal. Non optimise davantage dans cette phase ("orchestration simple suffit").
- Selon l'ancre de resolution retenue, le niveau de detail differe entre les blocs : un ancrage Autopilot donne un profil complet mais un bloc Entra allege (`isManaged`/`isCompliant` non disponibles, le type `EntraDevice` leger de Phase 3 ne les expose pas) ; un ancrage Entra donne un Entra complet mais un bloc Autopilot sans profil (jamais d'appel beta implicite, D025 applique une seconde fois). C'est un compromis assume, pas un bug : voir "Pourquoi aucun nouvel endpoint Graph" dans `docs/ARCHITECTURE.md`.
- La detection de conflit d'identifiants (`ResolvedIdentity.conflicts`) est purement presentationnelle et n'a pas de seuil de tolerance particulier (comparaison stricte apres trim/casse) ; elle peut donc se declencher sur les memes cas de figure que `identifier_mismatch` (Phase 4) - voir la limitation correspondante ci-dessus concernant le risque de faux positif sur un appareil reimage.

## Validation tenant reel

**Statut : non effectuee (Phases 4, 5 et 6).** Aucune App Registration n'a encore ete creee cote tenant (au 2026-09-14). Les Phases 4, 5 et 6 ont ete validees uniquement via des clients Graph factices (`tests/test_autopilot*.py`, `tests/test_entra*.py`, `tests/test_workspace.py`) plus une revue statique du code (echappement OData, capture d'erreur generique 4xx/429/5xx, chemins de repli). Rien ci-dessus n'a ete confirme contre un vrai tenant Microsoft. A refaire des qu'une App Registration avec les 3 permissions (`DeviceManagementManagedDevices.Read.All`, `Device.Read.All`, `DeviceManagementServiceConfig.Read.All`) et l'Admin Consent est disponible. Voir `NEXT.md`.

## Admin Consent

Comme l'application fonctionne en app-only, un administrateur doit accorder l'Admin Consent sur les permissions Application.
