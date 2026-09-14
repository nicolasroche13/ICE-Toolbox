# Fonctionnalites

## Phase 1 - Deployment Tools

- [x] Import CSV/XLSX/XLSM.
- [x] Simple Split.
- [x] Progressive Rings.
- [x] Custom Sizes avec Remaining.
- [x] Exclusions.
- [x] Stratification.
- [x] Representative Pilot.
- [x] Preview et export CSV/XLSX.

## Phase 2 - Graph et Intune Device Inspector

- [x] Configuration Microsoft Graph dans Settings.
- [x] Authentification app-only par Client Credentials.
- [x] Secret stocke via keychain systeme avec `keyring`.
- [x] Client Graph GET-only.
- [x] Pagination `@odata.nextLink`.
- [x] Erreurs 401, 403, 404, 429, timeout et reseau.
- [x] Retry 429 avec `Retry-After`.
- [x] Test Connection reel sur Graph.
- [x] Recherche Intune managed devices par nom.
- [x] Selection d'un device parmi les resultats.
- [x] Device Inspector : badges, issues, overview, raw JSON, diagnostic Graph.
- [x] Issues deterministes : non-compliance, stale check-in, non chiffre, no primary user, OS manquant.
- [x] Seuil stale device configurable, defaut 7 jours.
- [x] Tests sans tenant Microsoft reel.

## Phase 2.5 - UX/UI refactor

- [x] Sidebar sombre avec navigation principale a une seule profondeur.
- [x] Header leger avec statut Graph.
- [x] Home avec recherche globale visuelle et quick tools.
- [x] Deployment Tools organise en Source, Configuration, Preview, Export.
- [x] Modes de distribution en cards/radio visuels.
- [x] Options avancees repliees par defaut.
- [x] Exclusions deplacees dans Advanced options.
- [x] Preview orientee cards/statistiques plutot que tableau permanent.
- [x] Device list deplacee dans une vue secondaire.
- [x] Intune Device Inspector exception-first avec issue cards.
- [x] Overview Device Inspector en groupes label/value.
- [x] Raw Data et Diagnostics en tabs secondaires.
- [x] Settings simplifie autour d'une card Microsoft Graph.
- [x] Composants UI reutilisables et QSS centralisee.

## Phase 3 - Device Health / Troubleshooting

- [x] Recherche device par nom, serial number, Intune Managed Device ID et Entra Device ID lorsque disponible via managedDevice.
- [x] Modele `DeviceHealth` consolide multi-source.
- [x] Correlation Intune / Entra ID par `azureADDeviceId` / `deviceId`.
- [x] Sources partielles : un 403 Entra ou Applications n'interrompt pas l'inspection Intune.
- [x] Health summary avec issues, echecs applicatifs et dernier check-in.
- [x] Issues deterministes enrichies avec id, severity, source et evidence.
- [x] Vue Compliance transparente basee sur les champs device-level disponibles.
- [x] Vue Applications avec regroupement Failed / Pending / Installed / Not applicable / Unknown.
- [x] Codes erreur applicatifs affiches en hex et decimal si possible, sans signification inventee.
- [x] Raw Data multi-source : Intune, Entra ID, Applications, Compliance.
- [x] Diagnostics par appel Graph avec permission-aware UI.
- [x] Refresh read-only depuis Microsoft Graph.

## Phase 3.1 - Durcissement "real tenant"

- [x] Compliance state distinct de UNKNOWN, jamais traite comme non-conforme.
- [x] `isEncrypted` et `accountEnabled` manquants (null) distincts de `false`.
- [x] Detected Apps et Deployment Status restent deux sources et deux capacites separees.
- [x] Correlation Entra ambigue (plusieurs matches) : aucun device choisi arbitrairement, issue dediee.
- [x] Doublons de serial number renvoyes tels quels, sans ecrasement silencieux.
- [x] Modele de capacites a six etats applique et teste (AVAILABLE, PARTIAL, UNAVAILABLE, PERMISSION_MISSING, API_UNAVAILABLE, ERROR).
- [x] Panne partielle (403, 404, endpoint beta indisponible) sans casser le Device Inspector.
- [x] `mobileAppTroubleshootingEvents` isole sur `/beta/` avec repli propre ; reste du client en v1.0.
- [x] Diagnostics enrichis (feature/source, endpoint, API version, status, duree, objets, request-id, client-request-id, date) y compris sur erreur.
- [x] Support Bundle exportable localement, toujours sanitise.
- [x] Sanitisation centrale reconnaissant cles snake_case et camelCase avant logs/exports/diagnostics.
- [x] Recherche trim + insensible a la casse (tolower) pour serial number et Entra Device ID.
- [x] Dates Graph normalisees en UTC, y compris les dates sans fuseau.

## Phase 4 - Autopilot Troubleshooter

- [x] Page Autopilot activee (navigation + quick tool Home).
- [x] Recherche par numero de serie (cas d'usage principal), Autopilot Device Identity ID, Intune Managed Device ID, Entra Device ID et nom de poste via Intune.
- [x] Normalisation des espaces dans le numero de serie ; pas de fuzzy matching ; aucune selection arbitraire en cas d'ambiguite.
- [x] Modele `AutopilotDeviceHealth` consolide : identite Autopilot, profil assigne, correlation Intune, correlation Entra ID, sources, capacites, erreurs partielles, raw data.
- [x] Carte de synthese immediate apres selection (numero de serie, Group Tag, profil, Intune, Entra ID, derniere communication).
- [x] Chaine visuelle Autopilot -> Profil -> Entra ID -> Intune -> Conformite avec etats OK/ATTENTION/ERREUR/INCONNU/NON DISPONIBLE.
- [x] Profil Autopilot : nom, type, etat d'assignation et date d'assignation lus depuis Graph beta, jamais deduits d'une appartenance a un groupe.
- [x] Group Tag affiche tel quel ; son absence n'est jamais traitee comme une erreur.
- [x] 10 regles Autopilot Health deterministes avec id/severity/source/evidence, respectant UNKNOWN != FALSE.
- [x] Panne partielle (Profil, Intune ou Entra en erreur) sans jamais casser le reste du diagnostic.
- [x] Endpoint beta (`windowsAutopilotDeviceIdentities?$expand=deploymentProfile`) isole, avec repli propre ; tout le reste du module reste en v1.0.
- [x] Cinq nouvelles capacites (Autopilot Identity, Enrollment Information, Autopilot Profile, Intune Correlation, Entra Correlation) sur le meme modele a six etats.
- [x] Sections Vue d'ensemble / Autopilot / Intune / Entra ID / Donnees brutes / Diagnostics, sans sous-onglets complexes.
- [x] Raw Data et Diagnostics etendus (source, endpoint, API version, status, duree, objets, request-id) via les memes fonctions de rendu que Device Inspector.
- [x] Support Bundle Autopilot dedie (`EndpointToolbox-Autopilot-{serial}-{timestamp}.zip`), sanitise par la meme fonction centrale que Phase 3.1.
- [x] Refresh read-only, aucun appel Graph ne bloque l'UI (meme mecanisme async que Device Inspector).

## Phase 5 - Entra ID Inspector

- [x] Page Entra ID activee (navigation + quick tool Home).
- [x] Recherche par Object ID Entra, `deviceId`, `displayName` (egalite exacte), numero de serie et Managed Device ID Intune (via correlation).
- [x] Aucune selection arbitraire en cas d'ambiguite (plusieurs objets Entra, plusieurs managedDevice correles).
- [x] Modele `EntraDeviceHealth` consolide : identite Entra ID complete, correlation Intune, correlation Autopilot legere, sources, capacites, erreurs partielles, raw data.
- [x] Carte de synthese immediate + chaine visuelle Entra ID -> Intune -> Autopilot -> Conformite (OK/ATTENTION/ERREUR/INCONNU/NON DISPONIBLE).
- [x] Proprietes Entra affichees : accountEnabled, isCompliant, isManaged, isRooted, operatingSystem(Version), trustType, profileType, deviceOwnership, enrollmentType, managementType, onPremisesSyncEnabled, registrationDateTime, approximateLastSignInDateTime, onPremisesLastSyncDateTime, complianceExpirationDateTime.
- [x] `alternativeSecurityIds` et `physicalIds` deliberement jamais lus (documentes "internal use only" par Microsoft, aucune valeur diagnostique).
- [x] 5 regles Entra Health deterministes, chacune individuellement justifiee (pas de nombre arbitraire) : `entra_device_disabled`, `entra_device_stale`, `managed_without_intune_correlation`, `correlation_ambiguous`, `critical_data_unavailable`. UNKNOWN != FALSE verifie par tests.
- [x] Definition precise de "stale" documentee : `approximateLastSignInDateTime` (Entra, 90 jours) explicitement distinct de `lastSyncDateTime` (Intune, 7 jours).
- [x] Regle `os_version_mismatch` deliberement ecartee (risque de faux positif connu des la conception, voir DECISIONS.md D026).
- [x] Panne partielle (Intune ou Autopilot en erreur, 401/403/404/429/5xx) sans jamais casser l'inspection Entra principale.
- [x] Aucun appel beta : toutes les proprietes utilisees existent en v1.0.
- [x] Trois nouvelles capacites (Entra Device, Intune Correlation, Autopilot Correlation) sur le meme modele a six etats.
- [x] Sections Vue d'ensemble / Entra ID / Intune / Autopilot / Donnees brutes / Diagnostics, sans sous-onglets complexes, sans dupliquer les pages Intune/Autopilot completes.
- [x] Support Bundle Entra dedie (`EndpointToolbox-Entra-{nom}-{timestamp}.zip`), sanitise par la meme fonction centrale.
- [x] Reutilisation explicite des mecanismes Phase 3.1/4 : compose `IntuneDeviceInspectorService` et `AutopilotInspectorService` plutot que de reimplementer leur logique de recherche/correlation.
- [x] Refresh read-only, asynchrone, meme mecanisme que Device Inspector/Autopilot.

## Hors perimetre actuel

- [ ] Application Deployment Monitoring complet.
- [ ] Compliance Policy troubleshooting detaille.
- [ ] Device Compare.
- [ ] Autopilot Import, modification de Group Tag, suppression de device, assignation de profil, Intune Sync.
- [ ] Autopilot Deployment Analyzer / Fleet Health.
- [ ] Entra User Inspector, Entra Group Inspector, utilisateurs/groupes Entra generiques.
- [ ] Disable/enable/delete device Entra ID.
- [ ] BitLocker, LAPS.
- [ ] Conditional Access.
- [ ] Licences, logs de connexion utilisateur.
- [ ] Toute action Intune, Entra ou Autopilot en ecriture.
