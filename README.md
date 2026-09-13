# Endpoint Toolbox

Endpoint Toolbox est une application desktop Python/PySide6 pour les ingenieurs Endpoint et Microsoft 365.

La Phase 2 ajoute une fondation Microsoft Graph strictement read-only et un premier outil Intune Device Inspector. La Phase 2.5 refond l'UX autour d'une interface plus simple, Figma-inspired, avec disclosure progressif. La Phase 3 transforme l'inspection en Device Health read-only multi-source.

## Perimetre actuel

- Application desktop PySide6, sans serveur web local.
- Navigation principale : Home, Intune, Entra ID, Autopilot, Deployment Tools, Settings.
- Deployment Tools : split, rings progressifs, tailles custom, exclusions, stratification, Representative Pilot, imports/exports.
- Settings : configuration Microsoft Graph app-only.
- Intune : recherche de managed devices et Device Inspector read-only.
- Device Health : correlation Intune / Entra ID, issues deterministes, compliance device-level, applications device-level, raw data multi-source.
- Graph : OAuth2 client credentials, token cache, GET uniquement, pagination, retry 429, erreurs lisibles.
- Secrets : Client Secret stocke dans le keychain systeme via `keyring`, jamais dans le JSON local.
- UX Phase 2.5 : sidebar sombre, header Graph, Home orientee quick tools, Deployment Tools en parcours Source / Configuration / Preview / Export, Intune exception-first.

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
4. Ajouter les permissions Microsoft Graph Application documentees dans `docs/GRAPH_PERMISSIONS.md`.
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

## Tests

```bash
pytest -q
```

Avec le virtualenv local :

```bash
./.venv/bin/python -m pytest -q
```

## Documentation

- `docs/ARCHITECTURE.md` : structure applicative et responsabilites.
- `docs/DECISIONS.md` : decisions produit et techniques.
- `docs/FEATURES.md` : fonctionnalites livrees et backlog.
- `docs/GRAPH_PERMISSIONS.md` : permissions Graph minimales.
- `docs/SECURITY.md` : posture securite.
- `docs/DEVELOPMENT.md` : guide de reprise.
- `docs/TESTING.md` : strategie de tests.
