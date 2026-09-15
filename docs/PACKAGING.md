# Packaging Windows (Phase 7)

Reference technique du packaging Windows portable d'Endpoint Toolbox : outil choisi,
configuration reproductible, resolution de chemins frozen, stockage de configuration
et de secrets sur Windows, et checklist de validation manuelle. Cette phase n'ajoute
aucune fonctionnalite metier, aucune permission Graph, aucune ecriture Graph : voir
`docs/ROADMAP.md` (Phase 7) et `NEXT.md`.

## Outil de packaging

**PyInstaller**, choisi sans alternative serieuse identifiee pour ce projet :

- Deja largement utilise pour des applications PySide6/Qt desktop, avec des hooks
  officiels integres pour PySide6 (`hook-PySide6*.py`, presents dans PyInstaller
  lui-meme depuis plusieurs versions majeures).
- `pyinstaller-hooks-contrib` fournit des hooks communautaires pour pandas et
  openpyxl (toutes deux dependances runtime d'Endpoint Toolbox), evitant d'ecrire et
  maintenir des `hiddenimports` manuels pour ces bibliotheques volumineuses.
- Aucune incompatibilite avec ce projet n'a ete identifiee en pratique : voir
  "Build reellement effectue" plus bas.

## Version Python cible

**Python 3.12** (version de l'environnement de developpement actuel, `.venv` a la
racine du depot). Choix justifie par compatibilite, pas par nouveaute :

- `PySide6==6.10.1` (deja fixe dans `requirements.txt`) declare `Requires-Python
  <3.15,>=3.9` sur PyPI - 3.12 est dans la plage supportee.
- PyInstoller 6.22.x supporte Python 3.12 sans reserve connue.
- Aucun changement de version Python n'a ete fait pour cette phase : le projet
  utilisait deja 3.12 en developpement.

## Structure des fichiers de packaging

```
packaging/windows/EndpointToolbox.spec   # configuration PyInstaller (onefile, windowed)
packaging/windows/version_info.txt       # metadonnees EXE Windows (VSVersionInfo)
requirements-build.txt                   # pyinstaller + pyinstaller-hooks-contrib (build uniquement)
scripts/build_windows.ps1                # build reproductible : venv, deps, tests, PyInstaller
resources/windows/README.md              # emplacement prevu pour une icone .ico future
app/version.py                           # source unique de la version applicative
app/core/paths.py                        # resolution dev/frozen + emplacements utilisateur
app/core/logging_setup.py                # filet de securite minimal (voir "Logs")
.github/workflows/windows-build.yml      # workflow manuel (workflow_dispatch), aucun secret
.github/workflows/windows-validate.yml   # workflow manuel de validation Phase 7.1 (keyring, AppData, Support Bundle, Defender)
```

Aucun de ces fichiers ne contient de Tenant ID, Client ID, Client Secret ou tout
autre identifiant reel.

## Fonctionnement frozen vs developpement

`app/core/paths.py` est le seul module autorise a lire `sys.frozen` / `sys._MEIPASS`
directement - consigne explicite de la Phase 7 ("Ne disperse pas `sys._MEIPASS`
partout dans le code"). Il expose :

- `is_frozen()` : `True` uniquement sous un executable PyInstaller.
- `frozen_resource_root()` : `sys._MEIPASS` (onefile) ou le dossier de l'executable
  (onedir) - utilise uniquement par `resource_path`.
- `resource_path(*parts)` : resout un fichier embarque (icone, template, donnee
  statique) en dev comme en frozen. **Rien dans le code actuel ne consomme encore
  cette fonction** - aucune icone, image, police ou template n'existe aujourd'hui
  dans le projet (`app/ui/styles.py` definit sa feuille de style comme une simple
  chaine Python, pas un fichier `.qss` externe). Elle est preparee pour le jour ou
  une ressource embarquee sera ajoutee (voir "Icone"), afin qu'aucun code UI n'ait
  a re-decouvrir `sys._MEIPASS` a ce moment-la.
- `user_data_dir()` / `user_log_dir()` : voir sections suivantes.

Le packaging ne depend du repertoire de travail courant (current working directory)
nulle part : `GraphConfigStore`, `GraphSecretStore`, les exports Support Bundle et
les dialogues de fichiers (`QFileDialog`) utilisent tous des chemins absolus resolus
via `app/core/paths.py`, `Path.home()` ou un choix explicite de l'utilisateur -
jamais un chemin relatif au `.exe` ou au dossier de lancement.

## Emplacement de la configuration (Windows / macOS / Linux)

`app/graph/config.py` (`GraphConfigStore`) resout desormais son dossier via
`app.core.paths.user_data_dir()` au lieu d'un `Path.home() / ".endpoint_toolbox"`
code en dur :

| Plateforme | Emplacement | Change par la Phase 7 ? |
| --- | --- | --- |
| Windows | `%APPDATA%\EndpointToolbox\graph_config.json` (repli `~\AppData\Roaming` si `APPDATA` est absent de l'environnement) | Nouveau (avant : pas de comportement Windows distinct documente) |
| macOS | `~/.endpoint_toolbox/graph_config.json` | **Inchange** - comportement preserve a l'identique |
| Linux | `~/.endpoint_toolbox/graph_config.json` | **Inchange** - comportement preserve a l'identique |

Le fichier ne contient jamais le Client Secret (voir "Credential Manager"). Il n'est
jamais place a cote de `EndpointToolbox.exe` : un dossier "portable" ne signifie pas
un stockage de configuration dans le dossier du programme (consigne explicite),
justement pour eviter tout probleme de permissions si le `.exe` est lance depuis un
dossier en lecture seule (Program Files, partage reseau, cle USB).

## Logs

Avant cette phase, Endpoint Toolbox n'ecrivait **aucun fichier de log** - aucun
module `logging` n'etait utilise nulle part dans le code. Cette phase ajoute un
filet de securite minimal, pas une fonctionnalite de journalisation applicative :

- `app/core/logging_setup.configure_logging()` installe un `RotatingFileHandler`
  (1 Mo x 3 fichiers) ecrivant dans `user_log_dir()` (`user_data_dir()/logs`, donc
  `%APPDATA%\EndpointToolbox\logs\endpoint_toolbox.log` sur Windows,
  `~/.endpoint_toolbox/logs/endpoint_toolbox.log` sur macOS/Linux), et un
  `sys.excepthook` qui journalise toute exception non interceptee avant de rappeler
  le hook precedent.
- Raison d'etre : `EndpointToolbox.exe` est compile avec `console=False` (voir
  "Console Windows") - sans cela, un crash au demarrage sur le poste d'un
  utilisateur serait totalement invisible et impossible a diagnostiquer a distance.
- Ce module ne recoit jamais de payload Graph, de token ni de Client Secret : il n'a
  aucun point d'appel qui pourrait en recevoir (contrairement au Support Bundle, qui
  passe par `sanitize_for_export`). Voir `docs/SECURITY.md`.

## Credential Manager (secrets)

**Aucun changement de mecanisme n'etait necessaire** : `app/graph/secrets.py`
(`GraphSecretStore`) utilisait deja `keyring`, qui selectionne automatiquement le
backend adapte a l'OS - `keyring.backends.Windows.WinVaultKeyring` (Windows
Credential Manager) sur Windows, Keychain sur macOS, un backend configure par
l'utilisateur sur Linux. Aucun chiffrement maison n'a ete introduit ni envisage.

Ce qui **a** ete ajoute pour la Phase 7 :

- `packaging/windows/EndpointToolbox.spec` declare explicitement
  `collect_submodules("keyring.backends")` et `copy_metadata("keyring")`. Raison :
  `keyring` decouvre ses backends via les entry points de son propre package
  (`importlib.metadata`), un mecanisme dynamique qu'un executable fige ne peut pas
  resoudre sans que PyInstaller embarque a la fois les modules de backend
  eux-memes et les metadonnees `.dist-info` du package - une incompatibilite
  connue et documentee de PyInstaller avec `keyring` si elle n'est pas traitee
  explicitement (le hook integre `hook-keyring.py` de PyInstaller couvre deja une
  partie de ce besoin ; la declaration explicite dans le `.spec` le rend
  independant de ce detail d'implementation de PyInstaller).
- `tests/test_secrets.py` (nouveau, 10 tests) : secret present, absent, supprime,
  mis a jour, isolation par tenant/client, et Credential Manager inaccessible
  (`SecureStorageUnavailable`) sur `get_secret`/`set_secret`/`delete_secret`,
  via un faux backend keyring en memoire - aucun test ne touche un vrai Credential
  Manager ou Keychain.

`graph_config.json` contient Tenant ID, Client ID et le seuil stale device -
**jamais** le Client Secret (verifie par `tests/test_config_store.py`,
`test_saved_file_contains_only_non_sensitive_fields`).

## Portabilite

"Portable" signifie : aucune installation Python, pip ou dependance manuelle sur le
poste cible - pas que les donnees utilisateur restent dans le dossier du programme.
Configuration (`%APPDATA%\EndpointToolbox\graph_config.json`) et secret (Windows
Credential Manager) restent dans les emplacements utilisateur standard Windows,
jamais a cote de `EndpointToolbox.exe`.

## Version applicative

`app/version.py` (`__version__ = "0.7.0"`) est la source unique de la version
utilisee pour les metadonnees de l'executable Windows. Elle est independante des
marqueurs `APP_VERSION = "phase-N"` deja presents dans chaque module Support Bundle
(`app/intune`, `app/autopilot`, `app/entra`, `app/workspace`) - ces marqueurs
identifient quel module a produit un bundle donne et ne sont pas modifies par cette
phase (voir DECISIONS.md D033).

## Metadonnees de l'executable

`packaging/windows/version_info.txt` (format `VSVersionInfo` de PyInstoller,
`--version-file`) :

| Champ | Valeur |
| --- | --- |
| Product Name | Endpoint Toolbox |
| File Description | Endpoint Toolbox |
| File Version / Product Version | 0.7.0.0 |
| Company Name | **absent** - aucune valeur reelle n'existe dans le projet, aucune n'est inventee |

Ce fichier doit etre mis a jour manuellement si `app/version.py` change (les deux
fichiers ne peuvent pas partager une source commune : `version_info.txt` est un
litteral Python execute par PyInstoller en dehors de tout import du package
applicatif).

## Icone

Aucune icone Endpoint Toolbox n'existe dans ce depot. Rien n'a ete genere
arbitrairement. `packaging/windows/EndpointToolbox.spec` verifie la presence de
`resources/windows/app.ico` a la compilation (`Path.exists()`) et l'attache a
`EndpointToolbox.exe` seulement si le fichier existe ; sinon l'executable est
compile avec l'icone par defaut de PyInstaller. Voir `resources/windows/README.md`
pour la procedure d'ajout ulterieure.

## Console Windows et DPI/HiDPI

- `console=False` dans le `.spec` : aucune fenetre console ne s'ouvre au lancement
  de `EndpointToolbox.exe`.
- Qt 6 (PySide6 6.x) active le scaling HiDPI automatiquement depuis Qt 6.0 -
  `AA_EnableHighDpiScaling` est deprecie et toujours actif par defaut ; aucun code
  applicatif ne le desactive. Aucune modification necessaire pour le support
  DPI/HiDPI.
- Aucune refonte UI : navigation, dialogs (`QFileDialog`), export Support Bundle et
  affichage francais restent strictement inchanges par cette phase.

## Script de build

`scripts/build_windows.ps1` (PowerShell, a executer sur Windows) :

1. Refuse de s'executer si `$IsWindows` est faux (PyInstaller ne cross-compile pas).
2. Cree/reutilise `.venv` a la racine du depot.
3. Installe `requirements.txt` + `requirements-build.txt`.
4. Lance `pytest -q` - arrete le build si un test echoue.
5. Lance `compileall` - arrete le build en cas d'erreur de compilation.
6. Lance `pyinstaller --noconfirm --clean packaging/windows/EndpointToolbox.spec`.
7. Verifie que `dist/EndpointToolbox.exe` existe, affiche son chemin et sa taille.

Aucun credential dans le script. Sortie non nulle (`exit 1`) et message clair a
chaque etape qui peut echouer.

## GitHub Actions (manuel)

`.github/workflows/windows-build.yml` : declenchement **uniquement**
`workflow_dispatch` (jamais sur push/PR), `runs-on: windows-latest`. Etapes :
checkout, setup Python 3.12, installation des dependances, tests, compileall,
PyInstaller, upload de `dist/EndpointToolbox.exe` comme artifact. Aucun Tenant ID,
Client ID ou Client Secret dans le workflow ; aucun appel Microsoft Graph ; aucune
publication de Release GitHub. **Execute reellement lors de la Phase 7.1** (voir
plus bas).

`.github/workflows/windows-validate.yml` (ajoute en Phase 7.1) : meme
declenchement manuel, meme runner. Reconstruit l'executable puis enchaine les
verifications scriptables reelles decrites dans "Phase 7.1" ci-dessous
(backend keyring, round-trip Credential Manager avec un secret de test non
sensible, Support Bundle synthetique, AppData/logs apres un lancement bref,
scan Defender non interactif). Aucun credential, aucun tenant, aucune Release.

## Build reellement effectue (Phase 7, macOS - test structurel historique)

Lors de la Phase 7, aucun build Windows reel n'avait ete effectue : le packaging
avait ete prepare sur macOS (Darwin arm64), et PyInstoller ne cross-compile pas un
`.exe` Windows depuis macOS ou Linux. Ce qui avait ete verifie a l'epoque, comme
test structurel uniquement :

- `pyinstaller --noconfirm --clean packaging/windows/EndpointToolbox.spec` execute
  jusqu'au bout sans erreur et produit un executable **macOS** fonctionnel,
  avec un seul avertissement attendu et sans consequence
  (`Hidden import "jinja2" not found` - dependance optionnelle de pandas, jamais
  utilisee par Endpoint Toolbox).
- L'application non figee demarrait correctement dans cet environnement.
- L'executable macOS genere n'avait pas pu etre demarre jusqu'au bout dans cet
  environnement sandboxe (limitation locale a macOS/Gatekeeper, sans rapport avec
  le bootloader Windows).

**Cette section est desormais depassee par la Phase 7.1 ci-dessous**, qui a
effectue un vrai build Windows et plusieurs validations reelles.

## Phase 7.1 - Build et validation reels sur Windows (GitHub Actions)

Realise le 2026-09-15 via le workflow GitHub Actions `windows-build.yml` sur un
runner GitHub-hoste `windows-latest` (Windows Server, environnement Windows reel,
mais **pas** un poste Windows 11 desktop interactif - voir "Ce qui reste non
valide" plus bas). Repo : `nicolasroche13/ICE-Toolbox` (remote ajoute pour cette
phase, avec l'accord explicite de l'utilisateur).

### Resultat du build

- Run : `windows-build.yml`, run ID 34933352669, declenchement manuel
  (`workflow_dispatch`), duree totale 2 min 53 s.
- Python reellement utilise : **CPython 3.12.10** (correspond a la cible
  documentee, 3.12).
- Installation des dependances : succes (`requirements.txt` + `requirements-build.txt`).
- Suite de tests : **190 passed** (aucune regression, execution reelle sur Windows,
  pas seulement sur macOS/Linux comme jusqu'ici).
- `compileall` : propre.
- PyInstoller : succes, aucun `hiddenimports` manquant bloquant - seul le meme
  avertissement attendu (`jinja2`) que sur macOS.
- **Aucune correction n'a ete necessaire** : le packaging a fonctionne des le
  premier build Windows reel.
- Artifact GitHub Actions `EndpointToolbox-windows` : un seul fichier,
  `dist/EndpointToolbox.exe` - aucun credential, aucune donnee de tenant.

### Artefact produit

| Propriete | Valeur |
| --- | --- |
| Nom | `EndpointToolbox.exe` |
| Taille | 77 275 947 octets (~73,7 Mio) |
| SHA-256 | `7ced561a47eb52357b6b7952a64adb1a8f1ff75f0149bed1e1faefff53f81374` |
| Format | PE32+ executable (GUI) x86-64, pour MS Windows (confirme via inspection binaire du fichier telecharge) |
| Mode | onefile confirme (`Build complete` de PyInstoller, un seul fichier dans l'artifact) |
| Console | **absente** - le format PE porte le sous-systeme **GUI** (pas CUI/console), confirmant `console=False` au niveau binaire, pas seulement dans la configuration source |

### Validations reelles effectuees (workflow `windows-validate.yml`, run ID 34933784341)

Workflow manuel dedie, ajoute pour cette phase (`.github/workflows/windows-validate.yml`), executant sur le meme type de runner Windows les verifications suivantes - toutes reelles, aucune simulee :

- **Backend keyring** : `keyring.get_keyring()` resout reellement vers
  `keyring.backends.Windows.WinVaultKeyring` - confirme, pas suppose.
- **Credential Manager (Windows)** : un secret **de test, non sensible**
  (`test-only-non-sensitive-placeholder`, sous un nom de service distinct de celui
  de l'application reelle) a ete ecrit, relu (`Round-trip OK via WinVaultKeyring`)
  puis supprime (`Deleted OK, get after delete -> None`) via le vrai Windows
  Credential Manager. Le mecanisme fonctionne reellement sur Windows.
- **AppData** : apres un lancement reel de `EndpointToolbox.exe` (processus reste
  actif au moins 8 secondes sans crash), `C:\Users\<user>\AppData\Roaming\EndpointToolbox\`
  a bien ete cree, avec `logs\endpoint_toolbox.log` a l'interieur - confirmant que
  `user_data_dir()`/`user_log_dir()` resolvent correctement une fois figes sur
  Windows reel. Le fichier de log est vide (aucun crash, donc rien a journaliser -
  comportement attendu du filet de securite minimal). Aucun `graph_config.json`
  n'a ete cree (normal : aucune interaction Settings n'a eu lieu dans ce test
  scripte, headless).
- **Emplacement hors du dossier de l'executable** : `AppData\Roaming\EndpointToolbox`
  est bien distinct du dossier contenant `EndpointToolbox.exe` (`dist\`) -
  confirme reellement, pas seulement par lecture du code.
- **Support Bundle** : genere avec succes a partir de donnees synthetiques
  (reutilisation du fixture existant `tests/test_support_bundle.py::_sample_result`,
  qui injecte deliberement de faux secrets pour tester la sanitisation), sur un
  vrai systeme de fichiers Windows : `support_bundle_validation_output\EndpointToolbox-PC-MRS-001-{timestamp}.zip`,
  ZIP lisible (`diagnostics.json` present), sanitisation confirmee (aucun des
  faux secrets injectes n'apparait dans le contenu extrait).
- **Microsoft Defender** : scan non interactif (`MpCmdRun.exe -Scan -ScanType 3`)
  de l'executable - **code de sortie 0 (aucune menace detectee)**. Limitation
  honnete : ce resultat provient d'un runner cloud GitHub Actions, dont la
  configuration Defender peut differer de celle d'un poste Windows 11 utilisateur
  reel (heuristiques cloud, reputation de fichier liee a la provenance) ; ce n'est
  pas une garantie absolue pour toute machine.

### Ce qui reste non valide (necessite un poste Windows 11 desktop interactif reel)

Un runner GitHub Actions `windows-latest` est un vrai Windows, mais **pas** "un
poste Windows 11 x64" au sens de la checklist ci-dessous - c'est un Windows Server
cloud, sans session utilisateur interactive. N'ont **pas** ete valides et
necessitent un humain sur un vrai Windows 11 :

- Double-clic depuis l'Explorateur Windows, apparence reelle de la fenetre
  principale, navigation a la souris, redimensionnement, dialogs `QFileDialog`.
- Rendu visuel DPI/HiDPI et affichage francais/accents a l'ecran (le code ne fait
  rien de special, voir "Console Windows et DPI/HiDPI", mais aucune capture
  d'ecran ni verification visuelle n'a ete faite).
- Persistance de la configuration a travers un vrai cycle fermeture/reouverture
  pilote depuis l'UI Settings (le mecanisme Credential Manager sous-jacent a ete
  valide par script - voir plus haut - mais pas le flux complet via l'interface).
- Le dialogue SmartScreen reel : declenche par le marqueur "Mark of the Web"
  (zone Internet) qu'un fichier recoit typiquement en etant telecharge via un
  navigateur - un exe construit et execute dans le meme job CI n'a pas ce marqueur
  et ne peut donc pas reproduire fidelement ce declenchement. Reste **non teste**.
- Temps de demarrage precis (premier lancement vs lancements suivants) et
  consommation memoire au repos : non mesures avec precision - seule
  confirmation obtenue, le processus reste actif au moins 8 secondes sans crash
  sur le runner CI.

## Phase 7.3 - Artefact de distribution reel (2026-09-15)

Livraison demandee explicitement : un `EndpointToolbox.exe` telechargeable reel,
avec analyse binaire et test de demarrage automatise integres au workflow de
build lui-meme. `windows-build.yml` a ete enrichi (pas de nouveau workflow cree)
avec trois etapes supplementaires apres la construction PyInstoller : analyse
binaire (`Get-Item`, `Get-FileHash`, `Get-AuthenticodeSignature`), test de
demarrage automatise (process-level uniquement), et scan Microsoft Defender.
L'artifact a ete renomme `EndpointToolbox-windows` -> `EndpointToolbox-Windows-x64`.

| Element | Valeur reelle observee |
| --- | --- |
| Run GitHub Actions | `windows-build.yml`, run 35014507021 |
| Commit construit | `4c12cfa` (branche `main`) |
| Runner | `windows-latest` (Windows Server, GitHub-hoste) |
| Python | 3.12.10 |
| Tests | **206 passed in 6.07s** |
| `compileall` | Propre (etape verte) |
| PyInstoller | Succes, seul avertissement attendu (`jinja2`, sans consequence) - **aucune correction necessaire, succes des le premier essai** |
| Fichier | `EndpointToolbox.exe`, 77 276 285 octets |
| SHA-256 (`Get-FileHash`, cote CI) | `2A3CED28CEC8F533C43817D41CE2F3481E15E9BBD4B8BDBEC57E00E13EC26BC3` |
| SHA-256 (verifie independamment apres telechargement local, macOS `shasum -a 256`) | `2a3ced28cec8f533c43817d41ce2f3481e15e9bbd4b8bdbec57e00e13ec26bc3` - **identique** |
| Format binaire (`file`, verifie localement) | PE32+ executable (GUI) x86-64, pour MS Windows |
| `Get-AuthenticodeSignature` | `Status: NotSigned` - **executable non signe** (aucune variable `CODESIGN_THUMBPRINT` sur le depot ; comportement par defaut attendu) |
| Test de demarrage automatise | Processus lance, **actif apres 8 secondes sans crash** (aucune dependance Python externe manquante), puis arrete proprement |
| AppData au premier lancement | `C:\Users\runneradmin\AppData\Roaming\EndpointToolbox\` **reellement cree** |
| Scan Microsoft Defender | **Code de sortie 0 (aucune menace detectee)** - `MpCmdRun.exe -Scan -ScanType 3` ; Defender non modifie, aucune exclusion creee |
| Artifact GitHub Actions | `EndpointToolbox-Windows-x64` - **uploade avec succes**, contient uniquement `EndpointToolbox.exe` |
| Signature publique | **NON** - certificat de test uniquement disponible (Phase 7.2), aucun certificat public n'existe pour ce projet |
| SmartScreen | **Non testable depuis GitHub Actions** (necessite le marqueur "telecharge depuis Internet", absent d'un fichier construit et teste dans le meme job) - a valider par l'utilisateur sur un poste Windows 11 reel |

**Cet artifact est celui a telecharger et utiliser** : `EndpointToolbox.exe`
non signe (aucun certificat public n'existe), correspondant exactement au code
du commit `4c12cfa`. Ne pas confondre avec la signature TEST demontree
techniquement en Phase 7.2 (`docs/CODE_SIGNING.md`) : ce certificat de test
n'a jamais ete utilise pour cet artifact et de toute facon ne survit pas a la
fin d'un run GitHub Actions (magasin de certificats de l'ephemeral runner
detruit avec lui) - il ne peut donc pas etre reutilise pour signer un futur
build sans recreer le certificat a chaque fois, et n'apporte aucune confiance
publique dans tous les cas.

**Chemin exact pour telecharger dans GitHub** :
`nicolasroche13/ICE-Toolbox` -> onglet **Actions** -> workflow **"Windows
portable build (manual)"** -> run du **15 septembre 2026** (commit `4c12cfa`,
run 35014507021) -> section **Artifacts** en bas de la page du run ->
**`EndpointToolbox-Windows-x64`**.

## Checklist de validation manuelle Windows 11

A executer par l'utilisateur sur un vrai poste Windows 11 x64 - la Phase 7.1 a
valide les points marques [x] via GitHub Actions (Windows reel mais non
interactif) ; les points marques [ ] necessitent encore un humain sur un poste
Windows 11 physique/VM interactif :

1. [x] Recuperer `EndpointToolbox.exe` (artifact `EndpointToolbox-Windows-x64` du run 35014507021, voir Phase 7.3 ci-dessus).
2. [ ] Lancer sur Windows 11 x64 (double-clic depuis l'Explorateur).
3. [x] Verifier l'absence de fenetre console (confirme au niveau binaire : sous-systeme PE GUI ; confirme aussi par un lancement reel sans fenetre console observee en CI).
4. [ ] Verifier le demarrage visuel de l'interface (fenetre principale, sidebar, navigation) - le processus demarre et reste actif (confirme), l'apparence n'a pas ete verifiee visuellement.
5. [ ] Ouvrir Settings (interaction UI non testee).
6. [ ] Enregistrer Tenant ID / Client ID via l'UI (non teste).
7. [x] Le Client Secret passe reellement par Windows Credential Manager (`WinVaultKeyring` confirme par script, hors UI).
8. [ ] Fermer l'application (cycle UI non teste).
9. [ ] Relancer l'application (cycle UI non teste).
10. [ ] Verifier la persistance de la configuration via l'UI (non teste ; le mecanisme sous-jacent - fichier + Credential Manager - est valide).
11. [x] Verifier que le Client Secret n'apparait jamais dans `graph_config.json` (verifie par test automatise `tests/test_config_store.py`, non re-verifie manuellement sur ce poste car aucun `graph_config.json` n'a ete cree dans ce run headless).
12. [ ] Test Connection (necessite un tenant Microsoft reel, toujours indisponible - voir NEXT.md).
13. [ ] Page Intune (UI non testee).
14. [ ] Page Autopilot (UI non testee).
15. [ ] Page Entra ID (UI non testee).
16. [ ] Page Appareil / Device Workspace (UI non testee).
17. [ ] Refresh/Actualiser sur chaque page (UI non testee).
18. [x] Export Support Bundle : mecanisme valide avec des donnees synthetiques (ZIP lisible, sanitisation confirmee) ; pas via le bouton UI reel.
19. [x] Creation et contenu de `%APPDATA%\EndpointToolbox\logs\endpoint_toolbox.log` : confirme reellement (fichier cree, vide, aucun secret).
20. [ ] Comportement Windows SmartScreen au premier lancement (non declenchable depuis un exe construit et execute dans le meme job CI - voir plus haut).

## SmartScreen

`EndpointToolbox.exe` n'est **pas signe numeriquement** dans cette phase (aucun
certificat de signature de code n'existe pour ce projet - signer sans certificat
reel aurait ete invente). Windows SmartScreen affichera tres probablement un
avertissement ("Windows a protege votre ordinateur" / editeur non reconnu) au
premier lancement **d'un fichier telecharge** (marque "zone Internet"). C'est un
comportement Windows normal et attendu pour tout executable non signe, pas un
defaut du packaging. L'utilisateur devra utiliser "Informations complementaires" >
"Executer quand meme" pour lancer l'application. **Ce comportement n'a pas ete
observe reellement** (voir Phase 7.1, "Ce qui reste non valide") : un exe compile
et execute dans le meme job CI n'a jamais recu le marqueur de telechargement qui
declenche SmartScreen. La signature de code reste explicitement hors perimetre de
cette phase (voir `docs/ROADMAP.md`).

## Antivirus / Microsoft Defender

Scan non interactif (`MpCmdRun.exe -Scan -ScanType 3`) de `EndpointToolbox.exe`
sur le runner GitHub Actions Windows de la Phase 7.1 : **code de sortie 0, aucune
menace detectee**. Aucune exclusion Defender n'a ete creee ni desactivee ; aucune
protection n'a ete modifiee. Limitation : un runner cloud CI peut avoir une
configuration Defender differente d'un poste utilisateur reel (heuristiques cloud,
reputation liee a la provenance du fichier) - ce resultat ne garantit pas
l'absence d'alerte sur toute machine Windows 11 reelle, notamment lors d'un
premier lancement d'un fichier telecharge depuis Internet.

## Limitations

- **Build Windows reel** : effectue (Phase 7.1, GitHub Actions `windows-latest`) -
  voir ci-dessus. Ce n'est toutefois **pas** un poste Windows 11 desktop
  interactif ; les points de la checklist marques [ ] restent a valider par un
  humain sur un tel poste.
- Taille de l'executable desormais mesuree : ~73,7 Mio (PySide6 complet est
  embarque ; aucune tentative d'exclusion de modules Qt n'a ete faite pour ne pas
  risquer de casser une fonctionnalite non testable interactivement).
- SmartScreen, rendu visuel DPI/HiDPI, affichage francais a l'ecran, cycle complet
  Settings via l'UI, temps de demarrage precis et consommation memoire au repos :
  non valides (necessitent un poste Windows 11 interactif reel - voir Phase 7.1,
  "Ce qui reste non valide").
- Le scan Defender de la Phase 7.1 provient d'un runner cloud CI, pas d'un poste
  utilisateur reel - a reconfirmer si possible sur un vrai Windows 11.
- Aucune signature de code, aucun installateur MSI, aucune auto-mise-a-jour -
  explicitement hors perimetre (voir `docs/ROADMAP.md`).
- Cette phase herite integralement des limitations de validation tenant reel des
  Phases 4, 5 et 6 (voir `NEXT.md`) : le packaging ne change rien a cet etat.
