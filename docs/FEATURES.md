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

## Hors perimetre actuel

- [ ] Application Deployment Monitoring complet.
- [ ] Compliance Policy troubleshooting detaille.
- [ ] Device Compare.
- [ ] Autopilot Inspector.
- [ ] Autopilot Deployment Analyzer.
- [ ] Entra User Inspector.
- [ ] Entra Group Inspector.
- [ ] Conditional Access.
- [ ] Toute action Intune ou Entra en ecriture.
