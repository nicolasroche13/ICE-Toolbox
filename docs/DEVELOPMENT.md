# Development

## Demarrage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Sous Windows :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Configuration App Registration

1. Microsoft Entra admin center > App registrations > New registration.
2. Copier Tenant ID et Client ID.
3. Certificates & secrets > New client secret.
4. API permissions > Add a permission > Microsoft Graph > Application permissions.
5. Ajouter `DeviceManagementManagedDevices.Read.All`.
6. Ajouter `Device.Read.All` pour la correlation Entra ID.
7. Ajouter `DeviceManagementServiceConfig.Read.All` pour Autopilot Troubleshooter (Phase 4).
8. Cliquer sur Grant admin consent.
9. Endpoint Toolbox > Settings > saisir Tenant ID, Client ID, Client Secret.
10. Test Connection puis Save Configuration.

Ne jamais committer Tenant ID, Client ID reel ou Client Secret.

## Modules importants

- `app/graph/auth.py` : OAuth2 client credentials.
- `app/graph/client.py` : client Graph GET-only.
- `app/graph/config.py` : configuration locale sans secret.
- `app/graph/secrets.py` : stockage secret via keyring.
- `app/intune/device_inspector.py` : recherche et inspection read-only.
- `app/intune/models.py` : objets `ManagedDevice`, `DeviceHealth`, sources et statuts applicatifs.
- `app/intune/health.py` : regles deterministes Device Health et parsers multi-source.
- `app/autopilot/inspector.py` : recherche et inspection Autopilot read-only (`AutopilotInspectorService`).
- `app/autopilot/models.py` : objets Autopilot ; reutilise `ManagedDevice`/`EntraDevice`/`DeviceIssue`/`SourceStatus`/`Capability` de `app.intune.models`.
- `app/autopilot/health.py` : parsers et regles deterministes Autopilot Health.
- `app/autopilot/support_bundle.py` : export Support Bundle Autopilot.
- `app/graph/factory.py` : `build_intune_device_inspector` et `build_autopilot_inspector`.
- `app/ui/main_window.py` : pages Settings, Intune, Autopilot et Deployment Tools.
- `app/ui/components.py` : cards, status badges, search boxes, collapsible sections et composants communs.
- `app/ui/styles.py` : QSS centralisee pour le langage visuel.

## Regles de contribution

- Toute nouvelle requete Graph applicative doit passer par `GraphReadOnlyClient`.
- Ne pas ajouter de POST/PATCH/PUT/DELETE Graph.
- Ne pas logger token, secret ou Authorization header.
- Garder la logique metier hors de `app/ui`.
- Ajouter des tests avec transport mocke pour tout nouveau endpoint.
- Documenter toute nouvelle permission dans `docs/GRAPH_PERMISSIONS.md`.
- Conserver le disclosure progressif : ne pas afficher options avancees, raw data ou grandes listes par defaut.
- Privilegier une tache principale par ecran.
- Toute regle Device Health doit vivre hors UI, avoir id/severity/source/evidence, etre deterministe et testee.
- Une source Graph optionnelle doit pouvoir echouer sans casser toute l'inspection device.

## Extension future

`ManagedDevice` doit rester enrichissable par plusieurs sources :

- Device Health ;
- Compliance Details ;
- Application Install Status ;
- Troubleshoot Device.

Autopilot Troubleshooter (Phase 4) est livre ; les extensions restantes (Fleet Health, Autopilot Import, Device Compare) restent hors perimetre tant qu'elles ne sont pas explicitement demandees.

Ne pas coupler les futures fonctionnalites a une seule reponse brute Graph.

## Tester sans tenant

Les tests Phase 3 utilisent des clients Graph factices dans `tests/test_device_health.py`. Les tests Phase 4 suivent le meme principe dans `tests/test_autopilot.py` (`AutopilotFakeGraphClient`). Pour ajouter une source, mocker la reponse HTTP/Graph attendue et couvrir au minimum :

- succes ;
- 403 permission manquante ;
- 404 partiel ;
- donnees absentes / nulles ;
- raw data et diagnostic.

## Reprendre le module Autopilot

Pour ajouter une fonctionnalite Autopilot (ex. Autopilot Import en ecriture dans une phase future) :

1. Lire `docs/GRAPH_ENDPOINTS.md` avant tout nouvel endpoint - confirmer v1.0 vs beta sur la documentation Microsoft Learn actuelle, jamais de memoire.
2. Toute nouvelle action d'ecriture reste hors du `GraphReadOnlyClient` existant (qui bloque POST/PATCH/PUT/DELETE par construction) : elle necessiterait un client distinct, une decision explicite documentee dans `docs/DECISIONS.md`, et l'accord de l'utilisateur avant implementation.
3. Reutiliser `app.intune.models` / `app.intune.device_inspector` / `app.intune.health` plutot que dupliquer (voir D019).
4. Toute regle Autopilot Health doit respecter UNKNOWN != FALSE et vivre dans `app/autopilot/health.py`, jamais dans l'UI.
