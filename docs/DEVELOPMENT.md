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
- `app/entra/inspector.py` : recherche et inspection Entra ID read-only (`EntraInspectorService`), compose Intune et Autopilot plutot que de dupliquer leur logique.
- `app/entra/models.py` : objets Entra ID ; reutilise `ManagedDevice`/`DeviceIssue`/`SourceStatus`/`Capability` de `app.intune.models` et `AutopilotSearchResult` de `app.autopilot.models`.
- `app/entra/health.py` : parsers et regles deterministes Entra Health.
- `app/entra/support_bundle.py` : export Support Bundle Entra.
- `app/workspace/service.py` : `DeviceWorkspaceService`, orchestration pure composant Intune/Autopilot/Entra (resolution d'identite, consolidation, aucune regle metier propre).
- `app/workspace/models.py` : `ResolvedIdentity`, `IdentityConflict`, `DeviceWorkspaceResult`, `AutopilotBlock`/`EntraBlock`/`IntuneBlock` (dataclasses de presentation, ne dupliquent aucun modele source).
- `app/workspace/support_bundle.py` : export Support Bundle "Appareil" (sept sections JSON dans une seule archive).
- `app/graph/factory.py` : `build_intune_device_inspector`, `build_autopilot_inspector`, `build_entra_inspector` et `build_device_workspace`.
- `app/ui/main_window.py` : pages Settings, Intune, Autopilot, Entra ID, Appareil (Device Workspace) et Deployment Tools.
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

Autopilot Troubleshooter (Phase 4), Entra ID Inspector (Phase 5, devices) et Device Workspace (Phase 6, vue "Appareil") sont livres ; les extensions restantes (Fleet Health, Autopilot Import, Device Compare, Entra User/Group Inspector, Conditional Access, historique/favoris/dashboard multi-device) restent hors perimetre tant qu'elles ne sont pas explicitement demandees.

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

## Reprendre le module Entra ID

Pour etendre l'inspection Entra ID (ex. Entra User Inspector dans une phase future) :

1. Lire `docs/GRAPH_ENDPOINTS.md` avant tout nouvel endpoint. Phase 5 (devices) est entierement v1.0 ; un elargissement vers users/groups introduit de nouvelles permissions (`User.Read.All`, `Group.Read.All`, ...) qui doivent etre documentees et validees explicitement avant implementation, jamais ajoutees par defaut.
2. Reutiliser `app.intune.models` / `app.autopilot.models` / `app.entra.models` plutot que dupliquer (voir D019, D024-D027).
3. Toute regle Entra Health doit respecter UNKNOWN != FALSE, avoir une justification metier individuelle (pas de quota arbitraire de regles), et vivre dans `app/entra/health.py`, jamais dans l'UI.
4. Avant d'ajouter une regle comparant deux champs de sources differentes (ex. type "mismatch"), evaluer d'abord si un delai de synchronisation normal entre les sources peut produire un faux positif attendu (voir D026) ; si oui, ne pas ajouter la regle sans discussion explicite.

## Reprendre le module Workspace (Appareil)

Pour etendre la vue "Appareil" (Phase 6) :

1. `app/workspace/` reste une couche d'orchestration pure (D028) : n'y ajouter aucune regle Health, aucun parsing Graph, aucun modele dupliquant un modele source. Toute nouvelle regle metier appartient au module specialise concerne (`app/intune`, `app/autopilot` ou `app/entra`), jamais a `app/workspace`.
2. Ne pas ajouter d'appel Graph d'enrichissement dans `DeviceWorkspaceService` pour "completer" un bloc de synthese (D032) ; l'asymetrie de detail selon l'ancrage est assumee, le lien "Ouvrir dans <module>" reste la voie prevue pour le detail complet.
3. Avant de modifier l'ordre de resolution d'identite (GUID : Intune -> Autopilot -> Entra ; texte : Autopilot serial -> Intune nom), relire D029 et D030 - l'ordre actuel n'est pas arbitraire, il compense un angle mort connu de la recherche par nom d'Autopilot.
4. `IdentityConflict` reste une aide de presentation (badge), jamais une source de severite ; ne pas la fusionner avec `identifier_mismatch` (D031).
5. Toute extension multi-device (historique, favoris, dashboard, comparaison, export CSV) est explicitement hors perimetre de Phase 6 et necessite une discussion explicite avant implementation.
