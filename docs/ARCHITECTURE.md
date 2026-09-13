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
- `app/ui/components.py` : composants visuels reutilisables.
- `app/ui/styles.py` : feuille de style centralisee et design tokens pratiques.
- `app/entra`, `app/autopilot` : placeholders pour phases ulterieures.
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
