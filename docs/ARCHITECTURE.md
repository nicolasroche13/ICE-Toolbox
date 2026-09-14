# Architecture

## Objectif

Endpoint Toolbox est une application desktop locale pour preparer, inspecter et diagnostiquer des donnees Endpoint / Microsoft 365.

- Plateforme cible principale : Windows 11.
- Developpement possible sur macOS.
- UI : PySide6.
- Traitement local : pandas / openpyxl.
- Microsoft Graph : app-only, read-only.
- Aucun serveur local, aucune base de donnees, aucune execution PowerShell arbitraire.

## Structure

- `main.py` : point d'entree minimal.
- `app/ui` : fenetres et widgets PySide6.
- `app/deployment` : Ring Builder local.
- `app/io` : import/export CSV/XLSX.
- `app/models` : dataclasses partagees Deployment Tools.
- `app/graph` : configuration, secret store, OAuth2, client GET-only, erreurs et transport HTTP.
- `app/intune` : services et modeles metier Intune read-only.
- `app/autopilot` : services et modeles metier Autopilot Troubleshooter read-only (Phase 4).
- `app/entra` : services et modeles metier Entra ID Inspector read-only (Phase 5).
- `app/ui/components.py` : composants visuels reutilisables.
- `app/ui/styles.py` : feuille de style centralisee et design tokens pratiques.
- `tests` : tests pytest sans tenant Microsoft reel.

## Graph read-only

Toutes les requetes Graph applicatives passent par `GraphReadOnlyClient`.

Le client :

- refuse toute methode HTTP autre que GET ;
- ajoute le token Bearer uniquement dans le transport ;
- gere pagination `@odata.nextLink` ;
- gere 401, 403, 404, 429, timeout et erreurs reseau ;
- respecte `Retry-After` sur 429 dans la limite configuree ;
- ne journalise pas token, secret ou header Authorization.

L'authentification utilise le flux OAuth2 client credentials :

`POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`

Ce POST est limite a l'obtention du token et n'est pas une operation Graph. Les appels Graph restent GET-only.

## Configuration et secrets

`GraphConfigStore` stocke localement Tenant ID, Client ID et seuil stale device dans `~/.endpoint_toolbox/graph_config.json`.

`GraphSecretStore` stocke le Client Secret via `keyring` dans le gestionnaire de secrets du systeme. Aucun fallback plaintext n'est autorise.

L'architecture prevoit une evolution vers plusieurs profils ou certificat, mais Phase 2 garde un profil simple.

## Intune Device Inspector et Device Health

`IntuneDeviceInspectorService` utilise uniquement :

- `GET /deviceManagement/managedDevices`
- `GET /deviceManagement/managedDevices/{managedDeviceId}`
- `GET /deviceManagement/managedDevices/{managedDeviceId}/users`
- `GET /devices`
- `GET /deviceManagement/managedDevices/{managedDeviceId}/detectedApps`
- `GET /deviceManagement/mobileAppTroubleshootingEvents` explicitement sur `/beta/` (`GRAPH_BETA_BASE_URL`), seul appel beta du client. Isole dans `_load_application_failures`, avec repli propre : un 403/404/erreur reseau sur cet endpoint ne casse jamais l'inspection et se traduit par une capacite `PERMISSION_MISSING`/`API_UNAVAILABLE`. Toutes les autres requetes restent en v1.0.

Le service transforme les reponses Graph en modele consolide :

- `ManagedDevice` : source Intune principale.
- `EntraDevice` : objet directory correle par `azureADDeviceId` / `deviceId`.
- `ApplicationStatus` : applications detectees et evenements d'installation applicatifs.
- `ComplianceSummary` : etat de conformite device-level expose par `managedDevice`.
- `DeviceHealth` : agregat read-only contenant donnees normalisees, sources brutes, provenance et erreurs partielles.

Une source peut echouer sans casser toute l'inspection. Exemple : Intune OK, Entra 403, Applications OK. L'UI affiche alors les donnees disponibles et signale la permission manquante dans Diagnostics.

## Issues detected

Les issues sont deterministes et implementees hors UI dans `app/intune/health.py` :

- non-compliance si `complianceState` est different de `compliant` et `unknown` (une valeur absente ou `unknown` n'est jamais traitee comme `false`) ;
- stale device si `lastSyncDateTime` depasse le seuil configure, par defaut 7 jours (une date absente ne genere aucune issue) ;
- Entra device non trouve lorsque l'ID Entra existe dans Intune, que la source Entra a repondu et qu'elle n'est pas ambigue ;
- Entra correlation ambigue lorsque plusieurs devices Entra correspondent au meme `azureADDeviceId` : aucun device n'est choisi arbitrairement, l'issue `entra.ambiguous` est levee a la place ;
- device desactive dans Entra ID ;
- device not encrypted si `isEncrypted` vaut explicitement `false` (une valeur absente ne genere aucune issue) ;
- no primary user si aucun primary user ni UPN n'est retourne ;
- serial number manquant ;
- model/manufacturer manquant ;
- OS information missing si OS ou version OS manque.
- echec applicatif si un statut applicatif de type `deployment_status` (pas `detected_app`) retourne `failed` ;
- very old enrollment with no recent check-in.

Chaque issue contient id, severity, title, description/reason, source et evidence. Toutes les dates Graph passent par `app.utils.time.parse_graph_datetime`, qui normalise en UTC et traite une date sans fuseau comme deja en UTC plutot que dans le fuseau local de la machine.

## Modele de capacites

`DeviceHealth.capabilities` expose, pour chaque source (Intune Device, Primary users, Entra Device, Compliance, Detected Apps, Deployment Status, Autopilot), un etat `AVAILABLE / PARTIAL / UNAVAILABLE / PERMISSION_MISSING / API_UNAVAILABLE / ERROR` avec la permission requise et une raison lisible. Une source non interrogee est `UNAVAILABLE`, un 403 devient `PERMISSION_MISSING`, un 404 devient `API_UNAVAILABLE`, toute autre erreur devient `ERROR`. Deployment Status reste `PARTIAL` par construction : les evenements de troubleshooting applicatif ne couvrent pas l'ensemble des echecs possibles.

## UI et threading

Les traitements de fichiers et les appels Graph passent par `TaskWorker` + `QThread`. Les widgets ne realisent pas directement les appels reseau.

## UX Phase 2.5

La refonte UI suit ces principes :

- progressive disclosure : les options avancees restent repliees par defaut ;
- one primary task per screen : chaque page sert une intention principale ;
- exception-first : Device Inspector affiche d'abord les issues ;
- technical details secondary : Raw Data, diagnostics et listes completes sont accessibles a la demande ;
- composants reutilisables : cards, status badges, search boxes, mode buttons et sections repliables ;
- Figma-inspired desktop design : sidebar sombre, cards blanches, espacements stables, palette sobre.

Deployment Tools est organise en quatre etapes visuelles : Source, Configuration, Preview, Export. Le tableau complet des devices est deplace dans une vue secondaire.

## Raw data et diagnostics

Le Device Inspector expose le JSON Graph brut par source : Intune Managed Device, Entra Device, Applications et Compliance, sans token ni secret. Le diagnostic affiche source, endpoint, status HTTP, duree, nombre d'objets retournes et erreur lisible en cas de permission manquante.

## Autopilot Troubleshooter (Phase 4)

Module dedie `app/autopilot/` :

- `app/autopilot/models.py` : `AutopilotIdentity`, `AutopilotProfileAssignment`, `AutopilotSearchResult`, `AutopilotDeviceHealth`, `AutopilotInspectorResult`. Reutilise directement `ManagedDevice`, `EntraDevice`, `DeviceIssue`, `SourceStatus`, `Capability`, `HealthStatus` et `CapabilityState` de `app.intune.models` plutot que de les dupliquer.
- `app/autopilot/health.py` : `parse_autopilot_identity`, `parse_autopilot_profile`, `generate_autopilot_issues` (regles deterministes, memes principes que `app/intune/health.py`).
- `app/autopilot/inspector.py` : `AutopilotInspectorService` (recherche + inspection), seul point d'appel Graph du module. Reutilise `parse_managed_device`, `MANAGED_DEVICE_SELECT`, `ENTRA_DEVICE_SELECT` et `_with_source` de `app.intune.device_inspector`, et `parse_entra_device` de `app.intune.health`.
- `app/autopilot/support_bundle.py` : export zip dedie, reutilise `sanitize_for_export` et `non_overwriting_path`.
- `app/graph/factory.py` expose `build_autopilot_inspector`, symetrique de `build_intune_device_inspector`.
- `AutopilotPage` (`app/ui/main_window.py`) ne contient aucune logique Graph : elle appelle uniquement `AutopilotInspectorService`.

### Endpoints Graph Autopilot

Voir `docs/GRAPH_ENDPOINTS.md` pour le detail complet (URL, version, proprietes, filtres, permissions). Resume :

- `GET /deviceManagement/windowsAutopilotDeviceIdentities` (recherche) et `/{id}` (get) : **v1.0**.
- `GET {beta}/deviceManagement/windowsAutopilotDeviceIdentities/{id}?$expand=deploymentProfile` : **beta uniquement** (profil de deploiement assigne et statut d'assignation ; aucun equivalent v1.0 documente pour cette relation). Isole, optionnel, avec repli propre - memes principes que D015 pour `mobileAppTroubleshootingEvents`.
- Correlation Intune (`managedDevices/{managedDeviceId}`) et Entra (`devices?$filter=deviceId eq '...'`) : reutilisation directe des endpoints v1.0 deja utilises par Device Health, a partir des identifiants renvoyes par l'identite Autopilot.

### Recherche Autopilot

`AutopilotInspectorService.search_devices` accepte numero de serie (cas d'usage principal), Autopilot Device Identity ID, Intune Managed Device ID, Entra Device ID (GUID) et nom de poste (via Intune). La resolution se ramene toujours a un numero de serie, seule cle interrogeable de maniere fiable sur `windowsAutopilotDeviceIdentities` :

1. GUID : tentative directe comme Autopilot Identity ID, puis comme Managed Device ID (bascule vers son `serialNumber`), puis comme Entra Device ID (bascule via `managedDevices?$filter=azureADDeviceId eq '...'` vers un `serialNumber`).
2. Non-GUID : recherche directe par `contains(serialNumber, ...)`, puis repli sur une recherche de nom de poste Intune (`contains(deviceName, ...)`) dont chaque `serialNumber` resultant est ensuite verifie sur Autopilot.

Un appareil resolu via Intune mais absent d'Autopilot est renvoye comme resultat "non enregistre" (`AutopilotSearchResult.id == ""`) plutot que d'etre silencieusement ignore : `AutopilotDeviceHealth` peut alors afficher la correlation Intune/Entra tout en signalant l'absence Autopilot (`autopilot_not_registered`). Aucune selection n'est jamais automatique en cas d'ambiguite (plusieurs devices Entra, plusieurs serials identiques) : tous les resultats plausibles sont renvoyes.

### Issues Autopilot

`app/autopilot/health.py` genere des `DeviceIssue` (id anglais, texte UI francais) : `autopilot_not_registered`, `profile_not_assigned`, `profile_assignment_failed`, `intune_device_missing`, `entra_device_missing`, `correlation_ambiguous`, `entra_device_disabled`, `intune_device_stale`, `identifier_mismatch`, `critical_data_unavailable`. Toutes respectent UNKNOWN != FALSE : un statut de profil `unknown`, un Group Tag absent ou une date manquante ne generent jamais une issue par defaut - seule une valeur confirmee (`notAssigned`, `failed`, 404 explicite, etc.) le fait. L'absence de Group Tag n'est delibarement jamais une issue (aucune regle fiable ne permet de l'affirmer comme anormale).

### Capacites Autopilot

Cinq capacites ajoutees au meme modele a six etats : `Autopilot Identity`, `Enrollment Information` (meme source que l'identite), `Autopilot Profile` (beta, isole), `Intune Correlation`, `Entra Correlation`.

## Entra ID Inspector (Phase 5)

Module dedie `app/entra/` :

- `app/entra/models.py` : `EntraDeviceDetail`, `EntraSearchResult`, `EntraDeviceHealth`, `EntraInspectorResult`. Reutilise `ManagedDevice`, `DeviceIssue`, `SourceStatus`, `Capability`, `HealthStatus` de `app.intune.models` et `AutopilotSearchResult` de `app.autopilot.models` plutot que de dupliquer ces types (meme principe que D019).
- `app/entra/health.py` : `parse_entra_device_detail`, `generate_entra_issues` (5 regles deterministes, memes principes que `app/intune/health.py` et `app/autopilot/health.py`).
- `app/entra/inspector.py` : `EntraInspectorService`, seul point d'appel Graph direct du module. Compose `IntuneDeviceInspectorService` et `AutopilotInspectorService` (memes instances, meme `GraphReadOnlyClient` partage) pour reutiliser leurs mecanismes de recherche existants plutot que de les reimplementer. Reutilise `MANAGED_DEVICE_SELECT`, `parse_managed_device` et `_with_source` de `app.intune.device_inspector`.
- `app/entra/support_bundle.py` : export zip dedie, reutilise `sanitize_for_export` et `non_overwriting_path`.
- `app/graph/factory.py` expose `build_entra_inspector`, qui construit et partage un `GraphReadOnlyClient` unique entre les trois services (Intune, Autopilot, Entra) pour eviter toute authentification redondante.
- `EntraPage` (`app/ui/main_window.py`) ne contient aucune logique Graph : elle appelle uniquement `EntraInspectorService`.

### Endpoints Graph Entra ID

Voir `docs/GRAPH_ENDPOINTS.md` pour le detail complet. Resume : **tout le module reste en v1.0**, aucun appel beta. `GET /devices/{id}` (Object ID direct), `GET /devices?$filter=...` (recherche par `deviceId` ou `displayName`, egalite exacte). Permission `Device.Read.All`, deja documentee et utilisee depuis Phase 3 - aucune permission supplementaire.

### Recherche Entra ID

`EntraInspectorService.search_devices` accepte l'Object ID Entra, le `deviceId` Entra, le `displayName` (egalite exacte), le numero de serie (via correlation Intune) et le Managed Device ID Intune (via correlation) :

1. GUID : tentative directe comme Object ID, puis comme `deviceId` (filtre, ambiguite geree comme pour Autopilot/Intune), puis comme Managed Device ID Intune (bascule via son `azureADDeviceId` vers `deviceId`).
2. Non-GUID : recherche directe par `displayName eq '...'`, puis repli sur `IntuneDeviceInspectorService.search_devices` (reutilisation directe, pas de reimplementation) dont chaque `azureADDeviceId` resultant est ensuite verifie sur Entra ID.

Aucune selection n'est jamais automatique en cas d'ambiguite : tous les resultats plausibles sont renvoyes pour selection manuelle.

### Correlation depuis un device Entra ID

- Intune : `GET managedDevices?$filter=azureADDeviceId eq '{deviceId}'`. Un resultat vide (200, 0 objet) est une correlation "non trouvee" confirmee ; un `>1` est une ambiguite (`correlation_ambiguous`) ; toute erreur Graph (401/403/404/429/5xx) est une correlation "inconnue" (capacite `PERMISSION_MISSING`/`API_UNAVAILABLE`/`ERROR`, jamais traitee comme confirmation d'absence).
- Autopilot : uniquement si la correlation Intune a reussi et fournit un numero de serie. Reutilise `AutopilotInspectorService.search_devices(serial)` (identite legere uniquement, jamais l'appel beta du profil) pour eviter de dupliquer la logique de recherche Autopilot ou d'ajouter un appel beta non necessaire a cette page.

### Issues Entra ID

`app/entra/health.py` genere volontairement **5 regles** (pas plus, chacune justifiee individuellement plutot qu'un nombre arbitraire) : `entra_device_disabled`, `entra_device_stale`, `managed_without_intune_correlation`, `correlation_ambiguous`, `critical_data_unavailable`. Toutes respectent UNKNOWN != FALSE : `accountEnabled`/`isManaged` absents (`None`) ne generent jamais d'issue, seule une valeur confirmee le fait.

Une regle `os_version_mismatch` (Entra `operatingSystemVersion` vs Intune `osVersion`) a ete deliberement **ecartee** : la divergence entre ces deux champs est un artefact frequent et attendu du delai de synchronisation entre Entra ID et Intune, pas necessairement une anomalie - l'ajouter aurait cree un risque de faux positif connu des la conception (voir D026). Les deux valeurs restent visibles cote a cote dans Raw Data / Diagnostics pour un examen manuel.

**Definition precise de "stale" (Entra)** : `entra_device_stale` se declenche lorsque `approximateLastSignInDateTime` depasse `ENTRA_STALE_SIGN_IN_DAYS` (90 jours, constante dans `app/entra/health.py`, non partagee avec le reglage "Seuil stale device" des Settings). Cette date mesure l'activite de connexion interactive Entra ID, **pas** le dernier check-in MDM Intune (`managedDevice.lastSyncDateTime`, cycle ~8h independant de l'activite utilisateur) : les deux ne doivent jamais etre confondues, et un seuil de 7 jours (pertinent pour Intune) generait un volume de faux positifs important si applique aux connexions Entra.

### Capacites Entra ID

Trois capacites sur le meme modele a six etats : `Entra Device`, `Intune Correlation`, `Autopilot Correlation`.
