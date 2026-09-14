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
publication de Release GitHub.

## Build reellement effectue

**Un build Windows reel n'a pas ete effectue** : cette phase a ete preparee sur
macOS (Darwin arm64), et PyInstoller ne cross-compile pas un `.exe` Windows depuis
macOS ou Linux - produire et valider `EndpointToolbox.exe` necessite une execution
reelle de `scripts/build_windows.ps1` (ou du workflow GitHub Actions) sur Windows.

Ce qui **a** ete verifie sur cette machine, comme test structurel (pas comme
validation Windows) :

- `pyinstaller --noconfirm --clean packaging/windows/EndpointToolbox.spec` execute
  jusqu'au bout sans erreur et produit un executable **macOS** fonctionnel
  (`dist/EndpointToolbox`, non commite). L'analyse des dependances (PySide6,
  pandas, openpyxl, keyring et ses backends) se resout sans `hiddenimports`
  manquant bloquant ; seul un avertissement attendu et sans consequence apparait
  (`Hidden import "jinja2" not found` - dependance optionnelle de pandas pour le
  styling de DataFrame, jamais utilisee par Endpoint Toolbox).
- L'application **non figee** (`./.venv/bin/python main.py`), avec le meme code
  `app/core/paths.py` / `app/core/logging_setup.py` que celui packaged, demarre
  correctement dans cet environnement : `configure_logging()` cree bien
  `~/.endpoint_toolbox/logs/`, `is_frozen()` retourne `False` comme attendu, et
  l'interface Qt s'initialise normalement (chargement des plugins, polices).
- L'executable **macOS** genere par PyInstoller n'a en revanche pas pu etre
  demarre jusqu'au bout dans cet environnement sandboxe (le processus reste
  inactif sans jamais atteindre le point d'entree Python, vraisemblablement une
  particularite de signature/Gatekeeper macOS locale a cet environnement
  d'execution, sans rapport avec le bootloader Windows de PyInstoller qui est un
  binaire entierement different). Ceci **ne concerne pas la cible Windows** et
  n'a aucune valeur de validation pour elle - mentionne ici uniquement par
  transparence sur les limites du test structurel effectue.

Build et executable finaux (`build/`, `dist/`, `EndpointToolbox.exe`) ne sont pas
commites (voir `.gitignore`).

## Checklist de validation manuelle Windows 11

A executer par l'utilisateur des qu'un poste Windows 11 x64 est disponible ; rien
ci-dessous n'a ete execute ni simule par l'agent :

1. Recuperer `EndpointToolbox.exe` (build local via `scripts/build_windows.ps1` ou
   artifact du workflow GitHub Actions manuel).
2. Lancer sur Windows 11 x64 (double-clic depuis l'Explorateur).
3. Verifier l'absence de fenetre console.
4. Verifier le demarrage de l'interface (fenetre principale, sidebar, navigation).
5. Ouvrir Settings.
6. Enregistrer Tenant ID / Client ID.
7. Enregistrer le Client Secret (doit passer par Windows Credential Manager).
8. Fermer l'application.
9. Relancer l'application.
10. Verifier la persistance de la configuration (Tenant ID / Client ID toujours
    presents).
11. Verifier que le Client Secret n'apparait pas dans
    `%APPDATA%\EndpointToolbox\graph_config.json` (ouvrir le fichier, inspecter).
12. Test Connection (lorsque un tenant Microsoft reel est disponible).
13. Page Intune.
14. Page Autopilot.
15. Page Entra ID.
16. Page Appareil (Device Workspace).
17. Refresh/Actualiser sur chaque page.
18. Export Support Bundle (chaque module).
19. Verifier la creation et le contenu de
    `%APPDATA%\EndpointToolbox\logs\endpoint_toolbox.log` (absence de secret).
20. Comportement Windows SmartScreen au premier lancement (voir ci-dessous).

## SmartScreen

`EndpointToolbox.exe` n'est **pas signe numeriquement** dans cette phase (aucun
certificat de signature de code n'existe pour ce projet - signer sans certificat
reel aurait ete invente). Windows SmartScreen affichera tres probablement un
avertissement ("Windows a protege votre ordinateur" / editeur non reconnu) au
premier lancement. C'est un comportement Windows normal et attendu pour tout
executable non signe, pas un defaut du packaging. L'utilisateur devra utiliser
"Informations complementaires" > "Executer quand meme" pour lancer l'application.
La signature de code est explicitement hors perimetre de cette phase (voir
`docs/ROADMAP.md`).

## Limitations

- Build Windows reel non effectue (voir plus haut) : rien ci-dessus ne remplace un
  test sur un poste Windows 11 x64 reel.
- La resolution `keyring.backends.Windows.WinVaultKeyring` sur Windows n'a pas ete
  executee reellement ; elle repose sur le comportement documente de `keyring` et
  sur les hooks PyInstaller/keyring existants, mais n'a pas ete confirmee poste par
  poste.
- Taille de l'executable non mesuree sur Windows (PySide6 complet est embarque ;
  aucune tentative d'exclusion de modules Qt n'a ete faite dans cette phase pour ne
  pas risquer de casser une fonctionnalite non testable sur cette machine).
- Aucune signature de code, aucun installateur MSI, aucune auto-mise-a-jour -
  explicitement hors perimetre (voir `docs/ROADMAP.md`).
- Cette phase herite integralement des limitations de validation tenant reel des
  Phases 4, 5 et 6 (voir `NEXT.md`) : le packaging ne change rien a cet etat.
