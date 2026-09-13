# Roadmap

## Phase 1 - Socle local et Deployment Tools

Statut : implemente.

- Ring Builder local.
- Import/export.
- Tests metier.

## Phase 2 - Microsoft Graph read-only et Intune Device Inspector

Statut : implemente.

- Settings Microsoft Graph.
- Authentification app-only.
- Keychain pour Client Secret.
- Client Graph GET-only.
- Intune Device Inspector.
- Issues detected deterministes.
- Raw Data et Graph Diagnostic.

## Phase 2.5 - UX/UI refactor

Statut : implemente.

- Sidebar sombre et header Graph.
- Home quick tools.
- Deployment Tools avec disclosure progressif.
- Intune Device Inspector exception-first.
- Composants UI reutilisables.
- Style centralise inspire du Figma.

## Phase 3 - Device Health / Troubleshoot read-only

Statut : implemente.

- Recherche par nom, serial number, Intune Managed Device ID et Entra Device ID.
- Modele Device Health multi-source.
- Correlation Intune / Entra ID.
- Compliance device-level transparente.
- Application status device-level read-only.
- Raw Data et Diagnostics multi-source.
- Refresh read-only.

## Phase 3.1 - Durcissement Device Health "real tenant"

Statut : implemente.

- Regles UNKNOWN != FALSE verifiees explicitement (compliance, isEncrypted, accountEnabled) et couvertes par tests.
- Detected Apps et Deployment Status restent deux capacites et deux jeux de donnees distincts, jamais fusionnes dans les issues.
- Compliance state reste distinct d'une raison detaillee non disponible (aucune raison inventee).
- Correlation Intune/Entra ID durcie : aucune selection arbitraire en cas d'ambiguite (`entra.ambiguous`), doublons de serial number non ecrases, tres anciens devices signales.
- Modele de capacites `AVAILABLE / PARTIAL / UNAVAILABLE / PERMISSION_MISSING / API_UNAVAILABLE / ERROR` applique a chaque source et teste.
- Panne partielle d'une source secondaire (403, 404, endpoint beta indisponible) sans casser l'inspection globale.
- Endpoint `mobileAppTroubleshootingEvents` isole explicitement sur `/beta/` avec repli propre ; toutes les autres sources restent en v1.0.
- Diagnostics enrichis : source, endpoint, API version, status HTTP, duree, objets retournes, request-id, client-request-id, date de reponse - y compris sur les reponses en erreur.
- Support Bundle exportable localement (zip + `diagnostics.json`), toujours passe par la sanitisation centrale.
- Sanitisation centrale reconnait les cles snake_case et camelCase (`client_secret`/`clientSecret`, `access_token`/`accessToken`, etc.) avant tout log/export/diagnostic.
- Recherche robuste par nom, serial number, Intune Managed Device ID et Entra Device ID : trim, comparaison insensible a la casse via `tolower()` pour les egalites, pas de fuzzy matching.
- Dates Graph toujours normalisees en UTC ; une date sans fuseau n'est plus interpretee dans le fuseau local de la machine.
- Tests supplementaires realistes : doublons, ambiguite Entra, 403/404 partiels, dates nulles/timezone, compliance/encryption manquantes vs false, endpoint beta indisponible, sanitisation du support bundle.

## Phase 4 - Autopilot read-only

- Autopilot Inspector.
- Fleet Health.
- Analyse de deploiement.

## Phase 5 - Entra ID read-only

- User Inspector.
- Group Inspector.
- Group Compare.
- Enterprise Apps / Service Principals.
- Conditional Access Inspector.
