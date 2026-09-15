# Prochaine etape

**NEXT = deux pistes independantes, aucune ne bloque l'autre :**
**(A) valider Phase 4 (Autopilot), Phase 5 (Entra ID Inspector) ET Phase 6 (Device Workspace / "Appareil") sur un tenant Microsoft reel** ;
**(B) valider les points interactifs restants de la checklist Windows 11 (Phase 7.1) sur un vrai poste Windows 11 desktop.**

## Etat exact au 2026-09-15

| Niveau | Phase 4 (Autopilot) | Phase 5 (Entra ID) | Phase 6 (Device Workspace) | Phase 7 (Packaging Windows) |
| --- | --- | --- | --- | --- |
| Implementation (code) | Terminee | Terminee | Terminee | Terminee |
| Tests mockes | Terminee, tous verts (34) | Terminee, tous verts (35) | Terminee, tous verts (28) | Terminee, tous verts (31) |
| `compileall` | Propre | Propre | Propre | Propre (confirme aussi sur Windows reel, Phase 7.1) |
| **Validation contre un tenant Microsoft reel** | **Non effectuee** | **Non effectuee** | **Non effectuee** | Sans objet (packaging n'appelle jamais Graph) |
| **Build Windows reel** | Sans objet | Sans objet | Sans objet | **Effectue (Phase 7.1, 2026-09-15)** - GitHub Actions `windows-latest`, `EndpointToolbox.exe` produit, 190 tests verts sur Windows reel |
| **Validation Windows 11 desktop interactive** | Sans objet | Sans objet | Sans objet | **Partiellement effectuee** - voir detail ci-dessous |

Total suite de tests : 190 (62 Phases 1 a 3.1 + 34 Autopilot + 35 Entra ID + 28 Device Workspace + 31 Packaging), tous verts, aucune regression - confirme a la fois localement (macOS) et sur un runner Windows reel (Phase 7.1).

Ne pas ecrire "Autopilot valide" ni "Entra ID valide" ni "Appareil valide" ni "Phase 4/5/6 tenant-validated" nulle part tant que la ligne correspondante n'est pas passee a "Terminee"/"Effectuee". Le packaging Windows (Phase 7) a en revanche reellement progresse : voir le detail complet dans `docs/PACKAGING.md` ("Phase 7.1 - Build et validation reels sur Windows").

## Phase 7.1 - ce qui a ete reellement valide le 2026-09-15

Via deux workflows GitHub Actions (`windows-build.yml` et le nouveau `windows-validate.yml`), executes sur un runner GitHub-hoste `windows-latest` (Windows Server reel, mais **pas** un poste Windows 11 desktop interactif) :

- Build reel : `EndpointToolbox.exe` produit (77 275 947 octets, SHA-256 `7ced561a47eb52357b6b7952a64adb1a8f1ff75f0149bed1e1faefff53f81374`), Python 3.12.10, 190 tests verts, `compileall` propre, PyInstoller sans correction necessaire.
- Format binaire confirme : PE32+ GUI x86-64 (absence de console confirmee au niveau du fichier, pas seulement de la configuration source).
- Backend keyring reellement resolu en `WinVaultKeyring` (Windows Credential Manager) ; round-trip d'un secret de test (non sensible) reussi (ecriture, lecture, suppression confirmee).
- `%APPDATA%\EndpointToolbox\logs\endpoint_toolbox.log` reellement cree apres un lancement de l'executable ; vide (aucun crash) ; jamais a cote de l'executable.
- Support Bundle genere avec des donnees synthetiques sur un vrai systeme de fichiers Windows : ZIP lisible, sanitisation confirmee (aucun secret injecte ne fuite).
- Scan Microsoft Defender non interactif de l'executable : aucune menace detectee (limitation : runner cloud, pas un poste utilisateur reel).

**Reste non valide** (necessite un humain sur un vrai poste Windows 11 desktop, impossible depuis un runner CI headless) : double-clic reel, apparence visuelle de l'interface, navigation/redimensionnement/dialogs a la souris, rendu DPI/HiDPI et affichage francais a l'ecran, cycle complet Settings via l'UI (saisie Tenant ID/Client ID/Client Secret, fermeture, reouverture, persistance observee visuellement), pages Intune/Autopilot/Entra ID/Appareil via l'UI, bouton Support Bundle reel, comportement SmartScreen reel (necessite un fichier marque "telecharge", pas reproductible dans le meme job CI qui l'a construit), temps de demarrage precis et consommation memoire au repos. Detail complet et checklist item par item : `docs/PACKAGING.md`.

## Pourquoi le reste n'est pas encore fait

**Tenant reel (A)** : aucune App Registration Microsoft Entra ID n'existe encore pour Endpoint Toolbox. Aucun `graph_config.json` avec des valeurs reelles, aucun secret reel dans un Keychain/Credential Manager. Les Phases 5, 6 et 7 ont chacune ete implementees sans attendre cette validation (demande explicite a chaque fois), mais Phases 5/6 restent non confrontees a un tenant reel. Phase 6 ne fait qu'orchestrer les Phases 4 et 5 : elle herite integralement de leurs inconnues de validation (voir `docs/TESTING.md`, Gaps connus). Phase 7 (packaging) n'appelle jamais Microsoft Graph et n'a donc aucune dependance a un tenant reel.

**Windows 11 interactif (B)** : un runner GitHub Actions `windows-latest` est un vrai Windows, mais c'est un Windows Server cloud sans session utilisateur interactive - il ne peut pas reproduire un double-clic humain, l'apparence visuelle reelle, ou le declenchement de SmartScreen (lie au marqueur "telecharge depuis Internet" qu'un exe construit et execute dans le meme job n'a jamais). Ces points necessitent un poste Windows 11 physique ou VM avec un humain devant l'ecran.

## Action que l'utilisateur doit faire lui-meme

### (A) Validation tenant reel (Phases 4, 5, 6)

1. Creer l'App Registration dans Microsoft Entra ID (checklist precise : voir `docs/GRAPH_PERMISSIONS.md` et `docs/DEVELOPMENT.md`).
2. Ajouter les 3 permissions Application deja documentees et accorder l'Admin Consent :
   - `DeviceManagementManagedDevices.Read.All`
   - `Device.Read.All`
   - `DeviceManagementServiceConfig.Read.All`
3. Configurer Endpoint Toolbox (Settings > Tenant ID / Client ID / Client Secret > Test Connection > Save Configuration). Note : Test Connection n'exerce que `DeviceManagementManagedDevices.Read.All` ; les permissions Entra ID et Autopilot ne se verifient qu'en utilisant reellement ces pages.
4. Revenir avec l'agent (Claude/Codex) pour reprendre la checklist de validation terrain :
   - **Autopilot** : recherche multi-identifiant, `contains(serialNumber, ...)`, profil beta, correlation Intune/Entra, les 10 Health rules, `identifier_mismatch` (risque de faux positif documente a verifier en priorite), erreurs partielles, Support Bundle, UI reelle.
   - **Entra ID** : recherche par Object ID / deviceId / displayName (egalite exacte) / serial / Managed Device ID, correlation Intune/Autopilot, les 5 Health rules, definition du seuil "stale" a 90 jours, erreurs partielles (401/403/404/429/5xx), Support Bundle, UI reelle.
   - **Appareil (Device Workspace)** : resolution d'identite sur les 6 types d'identifiant (ordre GUID Intune -> Autopilot -> Entra ; ordre texte Autopilot serial -> Intune nom), detection de conflit d'identifiants (`IdentityConflict`) sur des valeurs reelles divergentes, consolidation Health/issues/capacites correcte face a des pannes partielles reelles, navigation "Ouvrir dans <module>" reutilisant bien l'identifiant deja resolu, Support Bundle "Appareil" unique, UI reelle.

### (B) Validation Windows 11 interactive restante (Phase 7.1)

1. Recuperer `EndpointToolbox.exe` : artifact `EndpointToolbox-windows` du workflow `windows-build.yml` (GitHub Actions, repo `nicolasroche13/ICE-Toolbox`), ou reconstruire localement via `scripts/build_windows.ps1` sur un poste Windows.
2. Sur un vrai poste Windows 11 x64, suivre les points **non coches** de la checklist dans `docs/PACKAGING.md` ("Checklist de validation manuelle Windows 11") : double-clic, apparence de l'UI, DPI/HiDPI, francais a l'ecran, cycle Settings complet via l'interface, pages Intune/Autopilot/Entra ID/Appareil, comportement SmartScreen reel (telecharger le fichier via un navigateur pour reproduire fidelement le marqueur "zone Internet" avant de le lancer).
3. Revenir avec l'agent pour consigner le resultat exact (coche/pas coche, comportement observe) dans `docs/PACKAGING.md`.

## Rappels stricts pendant cette validation

- Strictement READ-ONLY : aucun POST/PATCH/PUT/DELETE Graph, aucune action Intune/Entra ID/Autopilot.
- Ne pas ajouter de permission Graph supplementaire sans la documenter et la valider avant implementation.
- Ne pas modifier `identifier_mismatch`, `os_version_mismatch` (deliberement non implementee, voir D026) ou toute autre regle Health avant d'avoir demontre un probleme reel avec des valeurs concretes.
- Ne pas modifier l'ordre de resolution d'identite du Workspace (D029/D030) ni fusionner `IdentityConflict` avec `identifier_mismatch` (D031) sans discussion explicite, meme face a un cas reel surprenant.
- Ne pas signer numeriquement `EndpointToolbox.exe` sans certificat de signature reel (D039) ; ne pas inventer de Company/Publisher dans les metadonnees de l'executable.
- Ne jamais committer de tenant ID reel, client ID reel, client secret (meme "de test" reutilisable), token, Authorization header, serial number reel ou device ID reel. Utiliser des valeurs sanitisees dans toute documentation.
- Ne jamais committer `build/`, `dist/`, un `.exe` genere ou `support_bundle_validation_output/`.
- Ne pas commencer la Phase 8 (Entra ID au-dela de l'inspection device : users, groups, Conditional Access) avant que les Phases 4, 5 et 6 soient validees en conditions reelles, et que les points interactifs restants de la Phase 7.1 aient ete valides sur un poste Windows 11 reel.
