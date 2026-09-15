# Testing

## Commande principale

```bash
pytest -q
```

Avec le virtualenv local :

```bash
./.venv/bin/python -m pytest -q
```

## Compilation Python

Sur macOS sandboxe :

```bash
PYTHONPYCACHEPREFIX=/private/tmp/endpointtoolbox-pycache ./.venv/bin/python -m compileall main.py app tests
```

## Tests sans tenant Microsoft

Les tests Graph n'appellent jamais Microsoft Graph.

Ils utilisent :

- transport HTTP factice ;
- reponses JSON mockees ;
- erreurs HTTP mockees ;
- secret store factice.

## Couverture actuelle

Deployment Tools :

- split egal ;
- population non divisible ;
- progressive rings ;
- arrondis ;
- custom sizes ;
- exclusions ;
- doublons ;
- stratification ;
- representative pilot ;
- stabilite avec seed ;
- imports/exports.

Graph :

- authentification client credentials ;
- GET read-only ;
- blocage POST/PATCH/PUT/DELETE ;
- pagination ;
- 401 ;
- 403 ;
- 404 ;
- 429 + retry ;
- timeout ;
- echec authentification.

Intune Device Inspector :

- recherche device ;
- recherche par serial number ;
- recherche par Intune Managed Device ID ;
- parsing managedDevice ;
- secret absent ;
- non-compliance ;
- stale device ;
- device non chiffre ;
- primary user manquant ;
- OS manquant.

Device Health :

- correlation Intune / Entra ID ;
- Entra missing ;
- Entra ambigu (plusieurs matches, aucun choix arbitraire) ;
- doublons de serial number non ecrases ;
- recherche serial number insensible a la casse et trim ;
- 403 partiel permission-aware ;
- 404 partiel sur source optionnelle (Applications) ;
- endpoint beta (`mobileAppTroubleshootingEvents`) indisponible sans casser l'inspection ;
- capacite PARTIAL (Deployment Status) et PERMISSION_MISSING (Entra) ;
- compliance/encryption manquantes (`None`) distinctes de non-conforme / `false` ;
- applications installees ;
- applications en echec ;
- Detected Apps distinct de Deployment Status dans les issues et capacites ;
- codes erreur applicatifs hex/decimal ;
- generation d'issues avec ids et severities ;
- dernier check-in recent non signale comme stale ;
- date de dernier check-in nulle geree sans crash ;
- dates avec offset explicite normalisees en UTC ;
- date sans fuseau assumee UTC, jamais interpretee dans le fuseau local ;
- raw data multi-source ;
- source status et diagnostics, y compris request-id/client-request-id/date sur erreur.

Sanitisation (`tests/test_sanitize.py`) :

- redaction Authorization, client secret, access/refresh/id token ;
- cles snake_case et camelCase (`client_secret` / `clientSecret`) ;
- structures imbriquees (listes, tuples, dictionnaires) ;
- champs non sensibles preserves tels quels.

Support Bundle (`tests/test_support_bundle.py`) :

- payload sanitise avant export (aucun secret, token ou header Authorization present) ;
- sections attendues presentes (health, capabilities, sources, graph_diagnostics, raw_sources) ;
- export zip local contenant `diagnostics.json` sanitise ;
- export non destructif (pas d'ecrasement d'un bundle existant).

Autopilot (`tests/test_autopilot.py`) :

- recherche par numero de serie, par Autopilot Device Identity ID, par Managed Device ID, par Entra Device ID et par nom de poste (bascule via Intune) ;
- serial inconnu (aucun resultat) ;
- plusieurs resultats pour un meme serial (aucune selection arbitraire) ;
- normalisation des espaces dans le numero de serie avant filtre Graph ;
- appareil resolu via Intune mais non enregistre dans Autopilot (`autopilot_not_registered`) ;
- inspection complete (Autopilot + Profil + Intune + Entra ID tous presents) ;
- Group Tag absent : aucune issue generee ;
- Intune manquant (Managed Device ID incoherent, 404), 403 partiel, 429 traite comme panne partielle ;
- Entra manquant, 403 partiel, correlation ambigue (plusieurs matches) ;
- appareil Entra desactive ;
- Intune stale (pas de communication recente) ;
- incoherence d'identifiant Entra entre Autopilot et Intune (`identifier_mismatch`) ;
- dates nulles gerees sans crash ;
- profil assigne (`assignedInSync`), non assigne, statut inconnu (aucune issue), assignation en echec ;
- endpoint beta du profil indisponible (404) et permission manquante (403), capacite degradee sans casser l'inspection ;
- toutes les sources secondaires en echec (`critical_data_unavailable`) ;
- 403 direct sur l'identite Autopilot elle-meme : propage (erreur primaire, pas une panne partielle).

Support Bundle Autopilot (`tests/test_autopilot_support_bundle.py`) :

- sanitisation du payload (secrets/tokens absents, y compris depuis le raw JSON Autopilot) ;
- sections attendues presentes ;
- nom de fichier `EndpointToolbox-Autopilot-{serial}-{timestamp}.zip` ;
- export non destructif.

Entra ID (`tests/test_entra.py`) :

- recherche par Object ID Entra, par `deviceId`, par `displayName` (unique et ambigu), echec (aucun resultat) ;
- recherche par Managed Device ID Intune et par numero de serie (bascule via `IntuneDeviceInspectorService.search_devices` reutilise) ;
- echappement OData des apostrophes dans un `displayName` ;
- inspection complete (Entra + Intune + Autopilot tous presents), capacites `AVAILABLE` ;
- `accountEnabled` true / false / `None` (UNKNOWN != FALSE) ;
- `isManaged` true sans correlation Intune (issue), `isManaged` `None` ou `false` sans correlation Intune (aucune issue) ;
- correlation Intune presente, absente (0 resultat confirme, pas une erreur), ambigue (plusieurs matches, aucun choix arbitraire) ;
- correlation Autopilot presente, absente (non enregistre), non tentee (pas de serial Intune disponible) ;
- panne partielle Intune 401/403/429/5xx et Autopilot 403 sans casser l'inspection Entra ;
- 403 direct sur l'objet Entra lui-meme : propage (erreur primaire, pas une panne partielle) ;
- `critical_data_unavailable` quand Intune et Autopilot echouent tous les deux ;
- connexion recente non signalee comme stale, connexion ancienne signalee stale (90 jours), date de connexion nulle geree sans crash.

Support Bundle Entra (`tests/test_entra_support_bundle.py`) :

- sanitisation du payload (secrets/tokens absents, y compris depuis le raw JSON Entra) ;
- sections attendues presentes ;
- nom de fichier `EndpointToolbox-Entra-{nom}-{timestamp}.zip` ;
- export non destructif.

Device Workspace (`tests/test_workspace.py`) :

- recherche par chacun des 6 identifiants supportes (numero de serie, nom du poste, Managed Device ID Intune, Entra Object ID, Entra `deviceId`, Autopilot Device Identity ID) ;
- ancrage GUID priorise Intune -> Autopilot -> Entra, verifie explicitement selon la source disponible ;
- ancrage texte priorise Autopilot (serial) -> Intune (nom, repli), y compris le cas ou seul Intune connait le device (`autopilot_results=[]`) ;
- combinaisons de sources presentes/absentes (Autopilot seul, Entra seul, Intune seul, toutes presentes, aucune) ;
- ambiguite a chaque etape de resolution (plusieurs candidats Intune/Autopilot/Entra) : aucune selection arbitraire ;
- panne partielle 403/429/5xx sur chacune des trois sources sans casser la vue consolidee ;
- `IdentityConflict` detecte quand deux sources rapportent des valeurs differentes pour le meme identifiant, sans creer de `DeviceIssue` et sans dupliquer `identifier_mismatch` ;
- UNKNOWN != FALSE preserve a travers la consolidation (aucun champ absent traduit en etat negatif) ;
- Health Summary, points d'attention et capacites consolides : agregation fidele des `DeviceIssue`/`Capability`/`SourceStatus` des trois modules, source d'origine toujours preservee ;
- Support Bundle "Appareil" : sept sections JSON attendues, sanitisation (secrets/tokens absents y compris dans le raw JSON de chaque source), nom de fichier `EndpointToolbox-Appareil-{nom}-{timestamp}.zip`, export non destructif ;
- Refresh read-only reutilisant le meme mecanisme asynchrone que les trois pages specialisees.

Packaging Windows (Phase 7) :

`tests/test_paths.py` (12 tests) :

- `is_frozen()` false en developpement, true quand PyInstoller pose `sys.frozen` ;
- `frozen_resource_root()` utilise `sys._MEIPASS` s'il existe, sinon le dossier de l'executable (onedir) ;
- `resource_path()` resout correctement en mode dev et en mode frozen (simule) ;
- `user_data_dir()` : `%APPDATA%\EndpointToolbox` sur Windows simule (avec et sans `APPDATA` dans l'environnement), `~/.endpoint_toolbox` inchange sur macOS/Linux simules ;
- l'emplacement de configuration n'est jamais un sous-dossier du dossier de l'executable frozen ;
- `user_log_dir()` est bien `user_data_dir()/logs`.

`tests/test_secrets.py` (10 tests), via un faux backend keyring en memoire (aucun vrai Keychain/Credential Manager n'est touche) :

- secret present (aller-retour set/get), absent (aucune exception), supprime, mis a jour (ecrasement) ;
- isolation des secrets entre tenant/client differents ;
- rejet d'un secret vide ;
- Credential Manager inaccessible (`SecureStorageUnavailable`) sur `get_secret`, `set_secret` et `delete_secret`.

`tests/test_config_store.py` (6 tests) :

- aller-retour save/load de Tenant ID, Client ID et seuil stale device ;
- `load()` retourne `None` si le fichier n'existe pas, `clear()` supprime le fichier (idempotent) ;
- le fichier ecrit ne contient jamais le mot "secret" ni un champ autre que `tenant_id`/`client_id`/`stale_device_days` ;
- `CONFIG_DIR` derive bien de `app.core.paths.user_data_dir()`.

`tests/test_logging_setup.py` (3 tests) :

- creation du dossier et du fichier de log sous `user_log_dir()` ;
- idempotence (`configure_logging()` appele deux fois n'ajoute pas de handler en double) ;
- aucune occurrence du mot "secret" dans le fichier de log apres usage normal.

Code Signing (Phase 7.2, `tests/test_code_signing_structure.py`, 16 tests structurels - aucune signature Authenticode reelle n'est mockee, voir "Gaps connus") :

- `scripts/build_windows.ps1` reste utilisable sans certificat (signature optionnelle, activee uniquement par `CODESIGN_THUMBPRINT`) ;
- aucun thumbprint ni URL de timestamp code en dur dans `build_windows.ps1` ou `sign_windows.ps1` ;
- `sign_windows.ps1` refuse un fichier inexistant, utilise `/fd sha256` (jamais `/fd sha1`), verifie immediatement (`Get-AuthenticodeSignature`, `signtool`) et peut sortir en erreur ;
- `verify_windows_signature.ps1` classe explicitement UNSIGNED/VALID/INVALID/UNTRUSTED ;
- `create_test_codesigning_cert.ps1` ne pretend jamais etre Microsoft ou une entreprise tierce, n'exporte pas la cle privee, ne modifie jamais Trusted Root/Trusted Publishers (comme les deux autres scripts) ;
- l'etape de signature de `windows-build.yml` est gardee par `vars.CODESIGN_THUMBPRINT` (jamais un `secrets.*`) et le workflow continue de produire/uploader un exe non signe par defaut ;
- `.gitignore` exclut `*.pfx`/`*.p12`/`*.key` sans exclure automatiquement `.cer`/`.crt` ;
- aucun fichier `.pfx`/`.p12`/`.key` ni aucun marqueur `BEGIN PRIVATE KEY` n'est suivi par Git (verifie via `git ls-files` / `git grep`) ;
- `docs/CODE_SIGNING.md` existe et couvre Timestamp/SmartScreen/GitHub Actions/certificat auto-signe.

## Gaps connus

- Pas encore de tests UI automatises : le build PySide6 local ne fournit pas de plugin platform `offscreen` ou `minimal`.
- Validation Windows Credential Manager : `tests/test_secrets.py` valide `GraphSecretStore` via un faux backend en memoire ; le backend reel `keyring.backends.Windows.WinVaultKeyring` a ete confirme reellement resolu et fonctionnel (round-trip d'un secret de test) sur Windows lors de la Phase 7.1 (voir `docs/PACKAGING.md`), hors du cadre de la suite pytest.
- Pas encore de tests contre un tenant de sandbox reel (Intune, Entra ID et Autopilot). Aucune App Registration n'existe encore cote tenant au 2026-09-15 ; toute la couverture Phase 1 a 7.2 (206 tests au total) repose sur des transports/clients Graph factices ou des assertions structurelles - jamais un vrai tenant.
- Pas encore de tests UI automatises pour Refresh et tabs Device Inspector / Autopilot / Entra ID / Appareil ; la logique sous-jacente est couverte par tests metier mockes.
- Autopilot specifiquement non valide contre un vrai tenant : recherche multi-identifiant, `contains(serialNumber, ...)` avec des serials reels, appel beta du profil, et surtout le risque de faux positif documente sur `identifier_mismatch` (voir `docs/GRAPH_PERMISSIONS.md`, section Validation tenant reel).
- Entra ID specifiquement non valide contre un vrai tenant : recherche par `displayName` (egalite exacte - comportement reel non confirme), `deviceId eq` sur devices, et la definition du seuil "stale" a 90 jours (jamais confrontee a des dates de connexion reelles).
- Device Workspace herite integralement des inconnues de validation d'Autopilot et d'Entra ID ci-dessus, puisqu'il ne fait qu'orchestrer ces deux modules et Intune ; aucun comportement de resolution/priorisation propre au Workspace n'a ete confronte a un tenant reel non plus (voir `docs/GRAPH_PERMISSIONS.md`, section Validation tenant reel).
- Packaging Windows (Phase 7) : build Windows reel effectue avec succes en Phase 7.1 (GitHub Actions, 2026-09-15) ; validation Windows 11 desktop interactive partiellement effectuee - voir `docs/PACKAGING.md` pour le detail exact de ce qui reste a un humain.
- Code Signing (Phase 7.2) : les 16 tests sont structurels (fichiers texte, git) - **aucun ne signe reellement un binaire** (necessite Windows + signtool + un certificat, ce que pytest ne peut pas mocker de maniere honnete). Le statut de validation Authenticode reelle est documente dans `docs/CODE_SIGNING.md` ("Etat reel de cette phase") et `NEXT.md`, jamais dans la suite de tests.
