# Prochaine etape

**NEXT = trois pistes independantes, aucune ne bloque les autres :**
**(A) valider Phase 4 (Autopilot), Phase 5 (Entra ID Inspector) ET Phase 6 (Device Workspace / "Appareil") sur un tenant Microsoft reel** ;
**(B) valider les points interactifs restants de la checklist Windows 11 (Phase 7.1) sur un vrai poste Windows 11 desktop** ;
**(C) decider si une signature de code reelle (Phase 7.2) est souhaitee, et avec quel type de certificat.**

## Etat exact au 2026-09-15

| Niveau | Phase 4 (Autopilot) | Phase 5 (Entra ID) | Phase 6 (Device Workspace) | Phase 7 (Packaging Windows) | Phase 7.2 (Code Signing) |
| --- | --- | --- | --- | --- | --- |
| Implementation (code) | Terminee | Terminee | Terminee | Terminee | Terminee (infrastructure) |
| Tests mockes/structurels | Terminee, tous verts (34) | Terminee, tous verts (35) | Terminee, tous verts (28) | Terminee, tous verts (31) | Terminee, tous verts (16 structurels) |
| `compileall` | Propre | Propre | Propre | Propre (confirme aussi sur Windows reel, Phase 7.1) | Propre |
| **Validation contre un tenant Microsoft reel** | **Non effectuee** | **Non effectuee** | **Non effectuee** | Sans objet (packaging n'appelle jamais Graph) | Sans objet |
| **Build Windows reel** | Sans objet | Sans objet | Sans objet | **Effectue (Phase 7.1, 2026-09-15)** - GitHub Actions `windows-latest`, `EndpointToolbox.exe` produit, tests verts sur Windows reel | Sans objet direct - build reste possible sans certificat (voir Phase 7.2) |
| **Validation Windows 11 desktop interactive** | Sans objet | Sans objet | Sans objet | **Partiellement effectuee** - voir detail ci-dessous | Sans objet |
| **Signature Authenticode reelle** | Sans objet | Sans objet | Sans objet | Sans objet | **Signature de TEST reellement effectuee (2026-09-15)** - voir detail ci-dessous et `docs/CODE_SIGNING.md`. Aucun certificat public. |

Total suite de tests : 206 (62 Phases 1 a 3.1 + 34 Autopilot + 35 Entra ID + 28 Device Workspace + 31 Packaging + 16 Code Signing structurel), tous verts, aucune regression.

Ne pas ecrire "Autopilot valide" ni "Entra ID valide" ni "Appareil valide" ni "Phase 4/5/6 tenant-validated" ni "EndpointToolbox.exe signe et valide publiquement" nulle part tant que la ligne correspondante n'est pas passee a "Terminee"/"Effectuee" avec une preuve concrete consignee. Le packaging Windows (Phase 7) a reellement progresse : voir `docs/PACKAGING.md`. L'infrastructure de signature (Phase 7.2) est prete mais reste **optionnelle et inactive par defaut** : voir `docs/CODE_SIGNING.md`.

## Phase 7.1 - ce qui a ete reellement valide le 2026-09-15 (build Windows)

Via deux workflows GitHub Actions (`windows-build.yml` et `windows-validate.yml`), executes sur un runner GitHub-hoste `windows-latest` (Windows Server reel, mais **pas** un poste Windows 11 desktop interactif) :

- Build reel : `EndpointToolbox.exe` produit (77 275 947 octets, SHA-256 `7ced561a47eb52357b6b7952a64adb1a8f1ff75f0149bed1e1faefff53f81374`), Python 3.12.10, 190 tests verts (avant l'ajout des tests Code Signing), `compileall` propre, PyInstoller sans correction necessaire.
- Format binaire confirme : PE32+ GUI x86-64 (absence de console confirmee au niveau du fichier, pas seulement de la configuration source).
- Backend keyring reellement resolu en `WinVaultKeyring` (Windows Credential Manager) ; round-trip d'un secret de test (non sensible) reussi (ecriture, lecture, suppression confirmee).
- `%APPDATA%\EndpointToolbox\logs\endpoint_toolbox.log` reellement cree apres un lancement de l'executable ; vide (aucun crash) ; jamais a cote de l'executable.
- Support Bundle genere avec des donnees synthetiques sur un vrai systeme de fichiers Windows : ZIP lisible, sanitisation confirmee (aucun secret injecte ne fuite).
- Scan Microsoft Defender non interactif de l'executable : aucune menace detectee (limitation : runner cloud, pas un poste utilisateur reel).

**Reste non valide** (necessite un humain sur un vrai poste Windows 11 desktop, impossible depuis un runner CI headless) : double-clic reel, apparence visuelle de l'interface, navigation/redimensionnement/dialogs a la souris, rendu DPI/HiDPI et affichage francais a l'ecran, cycle complet Settings via l'UI, pages Intune/Autopilot/Entra ID/Appareil via l'UI, bouton Support Bundle reel, comportement SmartScreen reel, temps de demarrage precis et consommation memoire au repos. Detail complet : `docs/PACKAGING.md`.

## Phase 7.2 - ce qui a ete reellement fait le 2026-09-15 (signature de code)

- `scripts/create_test_codesigning_cert.ps1`, `scripts/sign_windows.ps1`, `scripts/verify_windows_signature.ps1` : crees, testes structurellement (16 tests, `tests/test_code_signing_structure.py`).
- `scripts/build_windows.ps1` et `.github/workflows/windows-build.yml` : signature optionnelle integree (variable `CODESIGN_THUMBPRINT`/`vars.CODESIGN_THUMBPRINT`), aucun impact sur le comportement par defaut (executable non signe).
- `docs/CODE_SIGNING.md` : reference complete (14 sections - pourquoi signer, garanties/limites Authenticode, 3 modes de certificat, 4 cas SmartScreen, timestamp, procedures, stockage de cle, GitHub Actions, futur certificat public, rotation).
- **Signature de TEST reellement effectuee** via `windows-codesign-validate.yml` (GitHub Actions `windows-latest`, run 35011776362) sur un `EndpointToolbox.exe` reellement construit dans le meme run :
  - Certificat de TEST cree (`Subject: CN=Endpoint Toolbox TEST Code Signing - DO NOT TRUST...`, thumbprint `4E19DC35D08C007530E78CA9AFA7EDA3FB91156F`) ;
  - signe en SHA-256 (`Hash of file (sha256): 2715597F8AA6CEB144A910C6B0961FD44A92058A9BA2C2F36BEEA6713D403DA0`), sans timestamp (aucune URL fournie) ;
  - **avant** confiance explicite : `signtool verify` et `Get-AuthenticodeSignature` rapportent tous deux une chaine de confiance non reconnue (`UnknownError`/1 erreur signtool) - `sign_windows.ps1` sort avec le code 1, **exactement comme concu** (etape 9 de sa specification) ;
  - **apres** import explicite (CI uniquement, `certutil -addstore -f Root`, jamais fait par les scripts livres) : `verify_windows_signature.ps1` classe `VALID`, `Get-AuthenticodeSignature` rapporte `Valid` ;
  - un bug reel a ete trouve et corrige dans cette phase : la premiere tentative (run 35010803489) est restee bloquee 5+ minutes sur `Import-Certificate -CertStoreLocation Cert:\CurrentUser\Root` (probable attente d'une confirmation interactive absente en CI headless) - corrige par `certutil.exe -addstore -f Root` (commit `f406bfc`), qui a fonctionne du premier coup a la seconde tentative.
  - Detail complet et tableau des resultats : `docs/CODE_SIGNING.md`, "Etat reel de cette phase".
- Aucun certificat public n'a ete achete ni choisi. Aucune validation SmartScreen reelle (fichier realiste marque "telecharge") n'a ete effectuee - necessite un poste Windows 11 interactif.

## Pourquoi le reste n'est pas encore fait

**Tenant reel (A)** : aucune App Registration Microsoft Entra ID n'existe encore pour Endpoint Toolbox. Aucun `graph_config.json` avec des valeurs reelles, aucun secret reel dans un Keychain/Credential Manager. Les Phases 5, 6 et 7 ont chacune ete implementees sans attendre cette validation (demande explicite a chaque fois), mais Phases 5/6 restent non confrontees a un tenant reel. Phase 6 ne fait qu'orchestrer les Phases 4 et 5 : elle herite integralement de leurs inconnues de validation (voir `docs/TESTING.md`, Gaps connus). Phase 7/7.2 (packaging/signature) n'appellent jamais Microsoft Graph et n'ont donc aucune dependance a un tenant reel.

**Windows 11 interactif (B)** : un runner GitHub Actions `windows-latest` est un vrai Windows, mais c'est un Windows Server cloud sans session utilisateur interactive - il ne peut pas reproduire un double-clic humain, l'apparence visuelle reelle, ou le declenchement de SmartScreen (lie au marqueur "telecharge depuis Internet" qu'un exe construit et execute dans le meme job n'a jamais). Ces points necessitent un poste Windows 11 physique ou VM avec un humain devant l'ecran.

**Signature de code (C)** : un certificat de TEST a ete cree et utilise reellement pour valider le mecanisme (voir Phase 7.2 ci-dessus) ; aucun certificat public n'existe pour ce projet et aucun fournisseur n'a ete choisi ni achete (explicitement hors perimetre Phase 7.2 - decision reservee a l'utilisateur). Voir `docs/CODE_SIGNING.md` pour le detail exact.

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

### (C) Decision signature de code (Phase 7.2)

1. Decider si une signature reelle est souhaitee pour les distributions d'`EndpointToolbox.exe` (developpement interne uniquement, ou distribution plus large).
2. Pour du developpement/test uniquement : `powershell -ExecutionPolicy Bypass -File scripts\create_test_codesigning_cert.ps1` sur un poste Windows, puis `scripts\sign_windows.ps1` avec le thumbprint affiche - voir `docs/CODE_SIGNING.md`, section 9.
3. Pour une distribution plus large : choisir (hors de cette phase, decision explicite de l'utilisateur) un fournisseur de certificat Code Signing public ou un service de signature cloud - voir `docs/CODE_SIGNING.md`, sections 6 et 13. Aucun fournisseur n'est presuppose ni recommande ici.
4. Revenir avec l'agent pour integrer le thumbprint choisi (jamais code en dur) et, le cas echeant, l'URL de timestamp reelle du fournisseur.

## Rappels stricts pendant cette validation

- Strictement READ-ONLY : aucun POST/PATCH/PUT/DELETE Graph, aucune action Intune/Entra ID/Autopilot.
- Ne pas ajouter de permission Graph supplementaire sans la documenter et la valider avant implementation.
- Ne pas modifier `identifier_mismatch`, `os_version_mismatch` (deliberement non implementee, voir D026) ou toute autre regle Health avant d'avoir demontre un probleme reel avec des valeurs concretes.
- Ne pas modifier l'ordre de resolution d'identite du Workspace (D029/D030) ni fusionner `IdentityConflict` avec `identifier_mismatch` (D031) sans discussion explicite, meme face a un cas reel surprenant.
- Ne jamais coder un thumbprint de certificat ou une URL de timestamp en dur (D041) ; ne jamais ajouter de PFX, mot de passe ou cle privee au depot ou a un secret GitHub Actions (D042) ; ne jamais faire modifier Trusted Root/Trusted Publishers automatiquement par un script (D043) ; ne pas inventer de Company/Publisher dans les metadonnees de l'executable.
- Ne jamais committer de tenant ID reel, client ID reel, client secret (meme "de test" reutilisable), token, Authorization header, serial number reel, device ID reel, fichier `.pfx`/`.p12`/`.key` ou cle privee.
- Ne jamais committer `build/`, `dist/`, un `.exe` genere ou `support_bundle_validation_output/`.
- Ne pas commencer la Phase 8 (Entra ID au-dela de l'inspection device : users, groups, Conditional Access) avant que les Phases 4, 5 et 6 soient validees en conditions reelles, et que les points interactifs restants des Phases 7.1/7.2 aient ete valides sur un poste Windows 11 reel.
