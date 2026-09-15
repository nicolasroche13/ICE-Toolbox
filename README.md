# Endpoint Toolbox

Endpoint Toolbox est une application desktop Python/PySide6 pour les ingenieurs Endpoint et Microsoft 365.

La Phase 2 ajoute une fondation Microsoft Graph strictement read-only et un premier outil Intune Device Inspector. La Phase 2.5 refond l'UX autour d'une interface plus simple, Figma-inspired, avec disclosure progressif. La Phase 3 transforme l'inspection en Device Health read-only multi-source. La Phase 4 ajoute un Autopilot Troubleshooter read-only. La Phase 5 ajoute un Entra ID Inspector (devices) read-only. La Phase 6 ajoute une vue "Appareil" (Device Workspace) read-only qui unifie Autopilot, Entra ID et Intune pour un meme poste. La Phase 7 prepare un packaging Windows portable (`EndpointToolbox.exe`, sans fonctionnalite metier nouvelle).

## Perimetre actuel

- Application desktop PySide6, sans serveur web local, interface entierement en francais (vocabulaire Microsoft Graph technique conserve en anglais).
- Navigation principale : Accueil, Appareil, Intune, Entra ID, Autopilot, Deployment Tools, Settings.
- Deployment Tools : split, rings progressifs, tailles custom, exclusions, stratification, Representative Pilot, imports/exports.
- Settings : configuration Microsoft Graph app-only.
- Intune : recherche de managed devices et Device Inspector read-only.
- Device Health : correlation Intune / Entra ID, issues deterministes, compliance device-level, applications device-level, raw data multi-source.
- Autopilot Troubleshooter : recherche par numero de serie (et autres identifiants), correlation Autopilot -> Profil -> Entra ID -> Intune, chaine visuelle, issues deterministes, Support Bundle dedie.
- Entra ID Inspector : recherche par Object ID, deviceId, displayName, numero de serie ou Managed Device ID, correlation Entra -> Intune -> Autopilot, chaine visuelle, issues deterministes, Support Bundle dedie. Aucun appel beta.
- Appareil (Device Workspace) : recherche unique par numero de serie, nom de poste, Managed Device ID Intune, Entra Object ID, Entra deviceId ou Autopilot Device Identity ID ; vue consolidee Autopilot/Entra ID/Intune sans dupliquer leurs regles metier ; acces direct vers chaque page specialisee ; Support Bundle unique.
- Graph : OAuth2 client credentials, token cache, GET uniquement, pagination, retry 429, erreurs lisibles.
- Secrets : Client Secret stocke dans le keychain systeme via `keyring`, jamais dans le JSON local.
- UX Phase 2.5 : sidebar sombre, header Graph, Home orientee quick tools, Deployment Tools en parcours Source / Configuration / Preview / Export, Intune/Autopilot/Entra ID/Appareil exception-first.

## Installation

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Configuration Microsoft Graph

1. Creer une App Registration dans Microsoft Entra ID.
2. Noter le Tenant ID et le Client ID.
3. Creer un Client Secret.
4. Ajouter les 3 permissions Microsoft Graph Application documentees dans `docs/GRAPH_PERMISSIONS.md` (`DeviceManagementManagedDevices.Read.All`, `Device.Read.All`, `DeviceManagementServiceConfig.Read.All`).
5. Accorder l'Admin Consent.
6. Ouvrir Endpoint Toolbox > Settings.
7. Saisir Tenant ID, Client ID et Client Secret.
8. Cliquer sur Test Connection.
9. Cliquer sur Save Configuration.

Le Client Secret est enregistre dans macOS Keychain ou Windows Credential Manager via `keyring`. Si aucun backend securise n'est disponible, Endpoint Toolbox refuse de sauvegarder le secret.

## Intune Device Inspector

Workflow :

1. Aller dans Intune.
2. Rechercher un poste par nom, serial number, Intune Managed Device ID ou Entra Device ID.
3. Selectionner un resultat.
4. Lire en priorite Health, Issues detected, conformite et dernier check-in.
5. Consulter Overview, Compliance, Applications, Raw Data et Diagnostics.
6. Utiliser Refresh pour relire Microsoft Graph, sans declencher d'action Intune.

Endpoint Toolbox n'execute aucune action Intune : pas de sync, restart, wipe, retire, delete ou modification.

## Autopilot Troubleshooter

Workflow :

1. Aller dans Autopilot.
2. Rechercher un appareil par numero de serie (cas d'usage principal), Autopilot Device Identity ID, Intune Managed Device ID, Entra Device ID ou nom de poste.
3. Selectionner un resultat (un appareil resolu via Intune mais absent d'Autopilot apparait comme "non enregistre").
4. Lire la carte de synthese, la chaine Autopilot -> Profil -> Entra ID -> Intune -> Conformite, puis les problemes detectes.
5. Consulter Vue d'ensemble, Autopilot, Intune, Entra ID, Donnees brutes et Diagnostics.
6. Utiliser Actualiser pour relire Microsoft Graph, sans declencher de synchronisation Autopilot ou Intune.

Endpoint Toolbox n'execute aucune action Autopilot : pas d'import, modification de Group Tag, suppression, assignation de profil ou synchronisation.

## Entra ID Inspector

Workflow :

1. Aller dans Entra ID.
2. Rechercher un appareil par Object ID, Device ID, nom d'appareil (displayName), numero de serie ou Managed Device ID Intune.
3. Selectionner un resultat.
4. Lire la carte de synthese, la chaine Entra ID -> Intune -> Autopilot -> Conformite, puis les problemes detectes.
5. Consulter Vue d'ensemble, Entra ID, Intune, Autopilot, Donnees brutes et Diagnostics.
6. Utiliser Actualiser pour relire Microsoft Graph, sans declencher d'action sur Entra ID, Intune ou Autopilot.

Endpoint Toolbox n'execute aucune action Entra ID : pas d'activation/desactivation, suppression de device, ni gestion d'utilisateurs, de groupes ou de Conditional Access.

## Appareil (Device Workspace)

Workflow :

1. Aller dans Appareil (juste apres Accueil).
2. Rechercher un poste par numero de serie, nom de poste, Managed Device ID Intune, Entra Object ID, Entra deviceId ou Autopilot Device Identity ID - une seule recherche, six types d'identifiant.
3. Lire la carte de synthese, la chaine Autopilot -> Profil -> Entra ID -> Intune -> Conformite, puis les points d'attention consolides (chaque probleme garde sa source d'origine visible).
4. Consulter la carte identite (tous les identifiants connus, avec leur source, et un badge si une incoherence est detectee entre deux sources).
5. Depuis les blocs Autopilot / Entra ID / Intune, cliquer "Ouvrir dans <module>" pour aller directement a la page specialisee correspondante sans ressaisir l'identifiant.
6. Consulter Donnees brutes et Diagnostics consolides par source.
7. Utiliser Actualiser pour relire Microsoft Graph via les trois modules, sans declencher aucune action sur le tenant.
8. Exporter un Support Bundle "Appareil" unique regroupant les sept sections (identite, health, capacites, Autopilot, Entra, Intune, diagnostics).

La vue Appareil n'introduit aucune nouvelle permission, aucun nouvel endpoint et aucun nouvel appel beta : elle orchestre uniquement les trois modules Autopilot, Entra ID et Intune deja existants.

## Version Windows portable

Endpoint Toolbox peut etre compile en `EndpointToolbox.exe` autonome (Windows 11 x64), sans installation Python/pip requise sur le poste cible :

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Le script installe les dependances, lance les tests, puis compile via PyInstoller (`packaging/windows/EndpointToolbox.spec`), et signe l'executable si (et seulement si) un certificat de signature est configure (voir `docs/CODE_SIGNING.md`) - aucun certificat n'est requis pour compiler. Doit s'executer sur Windows - PyInstoller ne cross-compile pas. Configuration et logs vont dans `%APPDATA%\EndpointToolbox\` (jamais a cote de l'executable) ; le Client Secret reste dans Windows Credential Manager, jamais dans `graph_config.json`. Detail complet, metadonnees de l'executable et checklist de validation manuelle Windows 11 : `docs/PACKAGING.md`.

Un build Windows reel a ete effectue avec succes le 2026-09-15 via GitHub Actions (`EndpointToolbox.exe`, 190 tests verts sur Windows reel) - voir `docs/PACKAGING.md` pour le detail exact et ce qui reste a valider par un humain sur un poste Windows 11 interactif. La signature de code reste optionnelle et son statut reel est documente dans `docs/CODE_SIGNING.md` et `NEXT.md`.

## Tests

```bash
pytest -q
```

Avec le virtualenv local :

```bash
./.venv/bin/python -m pytest -q
```

## Documentation

- `NEXT.md` : prochaine etape exacte pour reprendre le projet.
- `docs/ARCHITECTURE.md` : structure applicative et responsabilites.
- `docs/DECISIONS.md` : decisions produit et techniques.
- `docs/FEATURES.md` : fonctionnalites livrees et backlog.
- `docs/GRAPH_PERMISSIONS.md` : permissions Graph minimales.
- `docs/GRAPH_ENDPOINTS.md` : reference technique de chaque endpoint Graph (URL, version, filtres, limitations).
- `docs/SECURITY.md` : posture securite.
- `docs/DEVELOPMENT.md` : guide de reprise.
- `docs/TESTING.md` : strategie de tests.
- `docs/PACKAGING.md` : packaging Windows portable (PyInstoller, chemins frozen, Credential Manager, checklist de validation).
- `docs/CODE_SIGNING.md` : signature Authenticode optionnelle (certificat test/interne/public, timestamp, SmartScreen, GitHub Actions).
