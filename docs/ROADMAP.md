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

## Phase 4 - Autopilot Troubleshooter read-only

Statut : implemente (tests mockes uniquement). **Validation contre un tenant Microsoft reel non effectuee** : aucune App Registration n'existe encore cote tenant au 2026-09-14. Voir `docs/GRAPH_PERMISSIONS.md` (section Validation tenant reel) pour le detail et le protocole a suivre des qu'un tenant sera disponible.

- Module `app/autopilot/` (models, health, inspector, support_bundle) independant de l'UI, meme architecture que Device Health.
- Recherche multi-identifiant (serial en priorite, Autopilot ID, Managed Device ID, Entra Device ID, nom de poste), toujours ramenee a un numero de serie pour interroger `windowsAutopilotDeviceIdentities`.
- Correlation Intune (`managedDeviceId`) et Entra ID (`azureADDeviceId` / `azureActiveDirectoryDeviceId`) reutilisant les mecanismes Phase 3.1 : pas de selection arbitraire, doublons geres, devices renommes non ambigus (correlation par ID, pas par nom).
- Profil de deploiement assigne (nom, type, etat et date d'assignation) lu via le seul appel beta du module, isole et avec repli propre ; jamais deduit d'une appartenance a un groupe.
- 10 regles Autopilot Health deterministes (`autopilot_not_registered`, `profile_not_assigned`, `profile_assignment_failed`, `intune_device_missing`, `entra_device_missing`, `correlation_ambiguous`, `entra_device_disabled`, `intune_device_stale`, `identifier_mismatch`, `critical_data_unavailable`), UNKNOWN != FALSE verifie par tests.
- Cinq capacites supplementaires sur le modele a six etats existant.
- Page Autopilot complete : synthese immediate, chaine visuelle, problemes detectes en priorite, sections Vue d'ensemble/Autopilot/Intune/Entra ID/Donnees brutes/Diagnostics, Support Bundle dedie, Refresh asynchrone.
- 34 tests dedies (recherche, correlation, profil, panne partielle, sanitisation du support bundle).

## Phase 4+ - Autopilot au-dela du troubleshooting (hors perimetre actuel)

- Autopilot Import / modification Group Tag / suppression / assignation de profil (ecriture, hors perimetre read-only).
- Fleet Health (vue agregee multi-device).
- Analyse de deploiement.

## Phase 5 - Entra ID Inspector (devices) read-only

Statut : implemente (tests mockes uniquement). **Validation contre un tenant Microsoft reel non effectuee** : aucune App Registration n'existe encore cote tenant au 2026-09-14 (meme situation que Phase 4). Voir `docs/GRAPH_PERMISSIONS.md` (section Validation tenant reel) et `NEXT.md`.

- Module `app/entra/` (models, health, inspector, support_bundle), meme architecture que Device Health et Autopilot ; compose `IntuneDeviceInspectorService` et `AutopilotInspectorService` plutot que de dupliquer leur logique de recherche.
- Recherche par Object ID Entra, `deviceId`, `displayName` (egalite exacte), numero de serie et Managed Device ID Intune (via correlation), toujours sans selection arbitraire en cas d'ambiguite.
- Identite Entra ID complete en v1.0 uniquement (accountEnabled, isCompliant, isManaged, isRooted, trustType, profileType, deviceOwnership, enrollmentType, managementType, dates) - **aucun appel beta**.
- 5 regles Entra Health deterministes et individuellement justifiees (`entra_device_disabled`, `entra_device_stale`, `managed_without_intune_correlation`, `correlation_ambiguous`, `critical_data_unavailable`) ; UNKNOWN != FALSE verifie par tests ; regle `os_version_mismatch` deliberement ecartee (risque de faux positif connu des la conception, D026).
- Definition de "stale" Entra (90 jours, `approximateLastSignInDateTime`) explicitement distincte du seuil Intune (7 jours, `lastSyncDateTime`).
- Trois capacites supplementaires sur le modele a six etats existant.
- Page Entra ID complete : synthese immediate, chaine visuelle Entra -> Intune -> Autopilot -> Conformite, sections Vue d'ensemble/Entra ID/Intune/Autopilot/Donnees brutes/Diagnostics, Support Bundle dedie, Refresh asynchrone.
- Aucune permission Graph supplementaire : reutilise `Device.Read.All` deja documente depuis Phase 3.
- 35 tests dedies (recherche, correlation, panne partielle 401/403/404/429/5xx, stale, sanitisation du support bundle).

## Phase 6 - Device Workspace (vue "Appareil" unifiee) read-only

Statut : implemente (tests mockes uniquement). **Validation contre un tenant Microsoft reel non effectuee**, meme situation que Phases 4 et 5. Voir `docs/GRAPH_PERMISSIONS.md` (section Validation tenant reel) et `NEXT.md`.

- Module `app/workspace/` (models, service, support_bundle) : couche d'orchestration pure, aucune nouvelle regle metier, aucun nouvel appel Graph au-dela d'une seule correlation Autopilot legere deja etablie (D025) reutilisee depuis un autre point d'entree.
- `DeviceWorkspaceService` compose `IntuneDeviceInspectorService`, `AutopilotInspectorService` et `EntraInspectorService` (memes instances, un seul `GraphReadOnlyClient` partage) plutot que de dupliquer leur logique de recherche ou de correlation.
- Recherche unifiee par numero de serie, nom du poste, Managed Device ID Intune, Entra Object ID, Entra deviceId et Autopilot Device Identity ID ; resolution "ancree" sur le premier service qui repond (Autopilot en priorite pour un serial reconnu, sinon Intune, sinon Entra pour un GUID), sans jamais choisir arbitrairement en cas d'ambiguite.
- `ResolvedIdentity` consolide les identifiants connus avec leur source d'origine et detecte les incoherences entre sources (`IdentityConflict`) sans dupliquer ni remplacer la regle `identifier_mismatch` d'Autopilot.
- Synthese globale (Health Summary), points d'attention consolides et capacites consolidees : agregation pure des `DeviceIssue`/`Capability`/`SourceStatus` deja produits par les trois modules, aucune nouvelle regle de severite.
- Page "Appareil" : recherche unique, carte de synthese, chaine visuelle Autopilot -> Profil -> Entra ID -> Intune -> Conformite, points d'attention, carte identite, trois blocs synthetiques (Autopilot/Entra/Intune) avec acces direct vers chaque page specialisee en reutilisant l'identifiant deja resolu (pas de nouvelle recherche automatique), Donnees brutes et Diagnostics consolides.
- Support Bundle "Appareil" dedie (`EndpointToolbox-Appareil-{nom}-{timestamp}.zip`), sept fichiers JSON distincts (identity/health/capabilities/autopilot/entra/intune/diagnostics) dans une seule archive sanitisee - pas trois ZIP imbriques.
- Aucune permission Graph supplementaire, aucun nouvel endpoint, aucun nouvel appel beta.
- 28 tests dedies (recherche par chaque identifiant, combinaisons de sources presentes/absentes, pannes partielles 403/429/5xx, ambiguite, conflit d'identifiants, UNKNOWN, consolidation, Support Bundle, Refresh).

## Phase 7 - Entra ID au-dela de l'inspection device (hors perimetre actuel)

- User Inspector.
- Group Inspector.
- Group Compare.
- Enterprise Apps / Service Principals.
- Conditional Access Inspector.
