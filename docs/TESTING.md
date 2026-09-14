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

## Gaps connus

- Pas encore de tests UI automatises : le build PySide6 local ne fournit pas de plugin platform `offscreen` ou `minimal`.
- Pas encore de validation Windows Credential Manager automatisee.
- Pas encore de tests contre un tenant de sandbox reel (Intune, Entra ID et Autopilot). Aucune App Registration n'existe encore cote tenant au 2026-09-14 ; toute la couverture Phase 1 a 4 repose sur des transports/clients Graph factices.
- Pas encore de tests UI automatises pour Refresh et tabs Device Inspector / Autopilot ; la logique sous-jacente est couverte par tests metier mockes.
- Autopilot specifiquement non valide contre un vrai tenant : recherche multi-identifiant, `contains(serialNumber, ...)` avec des serials reels, appel beta du profil, et surtout le risque de faux positif documente sur `identifier_mismatch` (voir `docs/GRAPH_PERMISSIONS.md`, section Validation tenant reel).
