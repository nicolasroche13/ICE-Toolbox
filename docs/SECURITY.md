# Securite

## Principes

- Aucune ecriture dans Entra ID, Intune ou Microsoft Graph.
- Client Graph applicatif limite a GET par garde-fou technique.
- Pas de serveur web local.
- Pas d'execution PowerShell arbitraire.
- Pas de telechargement/execution dynamique de code.
- Pas de secret dans le code source, les logs ou la documentation.
- Pas de tenant ID reel dans le repository.

## Secrets

Tenant ID et Client ID sont stockes dans un fichier JSON local (`graph_config.json`, voir "Emplacements Windows" pour son chemin exact selon l'OS).

Le Client Secret est stocke via `keyring`, jamais dans `graph_config.json` :

- macOS : Keychain si disponible ;
- Windows : Credential Manager si disponible ;
- Linux : backend keyring configure par l'utilisateur.

Si aucun backend securise n'est disponible, Endpoint Toolbox ne sauvegarde pas le secret et affiche une erreur (`SecureStorageUnavailable`, teste dans `tests/test_secrets.py` : secret present, absent, supprime, mis a jour, Credential Manager inaccessible).

## Logs et diagnostics

Les diagnostics Graph peuvent afficher :

- source fonctionnelle ;
- endpoint appele ;
- status HTTP ;
- duree ;
- nombre d'objets retournes.

Ils ne doivent jamais afficher :

- access token ;
- Client Secret ;
- header Authorization.

Le support bundle (`app/intune/support_bundle.py`, `app/autopilot/support_bundle.py` et `app/entra/support_bundle.py`) passe systematiquement par `app/utils/sanitize.py` avant export. La sanitisation reconnait les cles sensibles en snake_case et en camelCase (`client_secret`/`clientSecret`, `access_token`/`accessToken`, `refresh_token`/`refreshToken`, `id_token`/`idToken`) ainsi que toute cle contenant `authorization`, de maniere recursive dans les dictionnaires, listes et tuples.

## Donnees utilisateur

Les fichiers importes par Deployment Tools ne sont pas conserves apres fermeture hors exports explicitement demandes.

Le Raw Data du Device Inspector contient uniquement le JSON Graph des sources lues pour le device affiche et peut etre exporte volontairement par l'utilisateur. Il est separe par source : Intune Managed Device, Entra Device, Applications et Compliance.

## Read-only Phase 3

Le bouton Refresh relit Microsoft Graph avec des GET. Il ne correspond pas a l'action Intune Sync et ne modifie pas le tenant.

Les echecs partiels sont traites localement :

- 403 sur une source : affichage permission manquante pour la section concernee ;
- 404 sur une source optionnelle : source indisponible ;
- aucune elevation ou permission ReadWrite n'est ajoutee automatiquement.

## Read-only Phase 4 (Autopilot)

Le module Autopilot est strictement read-only comme le reste de l'application :

- aucun POST/PATCH/PUT/DELETE Graph, y compris pour Group Tag, assignation de profil, import ou suppression de device ;
- aucune action `assignUserToDevice`, `updateDeviceProperties`, `deleteDevices` ou `assign` (profil) n'est implementee, meme si ces actions existent dans l'API Graph Autopilot ;
- le bouton Refresh de la page Autopilot relit Graph en GET et ne declenche ni synchronisation Autopilot ni synchronisation Intune ;
- le Support Bundle Autopilot (`app/autopilot/support_bundle.py`) passe par la meme sanitisation centrale que le Support Bundle Intune avant export.

## Read-only Phase 5 (Entra ID)

Le module Entra ID Inspector est strictement read-only comme le reste de l'application :

- aucun POST/PATCH/PUT/DELETE Graph, y compris pour activer/desactiver ou supprimer un device Entra ID (actions qui existent dans l'API Graph mais ne sont pas implementees) ;
- aucune lecture d'utilisateurs, groupes ou Conditional Access : le module reste limite aux devices, permission `Device.Read.All` uniquement ;
- `alternativeSecurityIds` et `physicalIds` (documentes "internal use only" par Microsoft) ne sont jamais lus ni exposes ;
- le bouton Actualiser de la page Entra ID relit Graph en GET et ne declenche aucune action sur Entra ID, Intune ou Autopilot ;
- le Support Bundle Entra (`app/entra/support_bundle.py`) passe par la meme sanitisation centrale que les autres Support Bundle avant export.

## Read-only Phase 6 (Device Workspace)

La page "Appareil" est une orchestration pure, strictement read-only :

- `app/workspace/` n'effectue aucun appel Graph direct hormis une reutilisation de `AutopilotInspectorService.search_devices` (meme methode, meme permission, meme endpoint GET deja utilise depuis Entra ID, D025) ; aucun endpoint, permission ou appel beta supplementaire n'est introduit ;
- aucun POST/PATCH/PUT/DELETE Graph : la page ne fait que composer les resultats deja lus par les trois modules Intune/Autopilot/Entra ;
- le bouton Refresh relit Graph en GET via les trois services composes et ne declenche aucune action sur le tenant ;
- les liens "Ouvrir dans <module>" naviguent vers une page specialisee deja read-only, sans jamais declencher d'action supplementaire ;
- le Support Bundle "Appareil" (`app/workspace/support_bundle.py`) passe par la meme sanitisation centrale que les autres Support Bundle avant export, pour chacune des sept sections JSON qu'il regroupe dans une seule archive.

## Packaging Windows (Phase 7)

Le packaging ne change aucune garantie de securite existante : `GraphReadOnlyClient` reste GET-only, aucun appel Graph n'est ajoute, aucune permission n'est ajoutee. Reference complete : `docs/PACKAGING.md`.

- **Emplacements Windows** : configuration (`graph_config.json`) dans `%APPDATA%\EndpointToolbox\`, jamais a cote de `EndpointToolbox.exe` - un dossier applicatif potentiellement en lecture seule (Program Files, partage reseau, cle USB) ne doit jamais etre un endroit ou ecrire des donnees utilisateur. macOS/Linux conservent `~/.endpoint_toolbox/` a l'identique.
- **Credential Manager Windows** : le Client Secret utilise le meme mecanisme `keyring` que macOS (Keychain), route automatiquement vers `keyring.backends.Windows.WinVaultKeyring`. Aucun chiffrement maison. `packaging/windows/EndpointToolbox.spec` declare explicitement les backends `keyring` (`collect_submodules`, `copy_metadata`) pour qu'ils restent decouvrables une fois l'executable fige - une incompatibilite connue de PyInstaller avec la decouverte de backends par entry points si elle n'est pas traitee.
- **Logs (Phase 7)** : un filet de securite minimal (`app/core/logging_setup.py`) ecrit dans `%APPDATA%\EndpointToolbox\logs\endpoint_toolbox.log` (Windows) ou `~/.endpoint_toolbox/logs/` (macOS/Linux), necessaire car l'executable est compile sans console (`console=False`, "Console Windows" ci-dessous). Ce fichier ne recoit jamais de payload Graph, de token ou de Client Secret - il ne journalise que le demarrage et les exceptions non interceptees (`sys.excepthook`), jamais un objet `GraphSettings` ou une chaine de secret.
- **Console Windows** : `EndpointToolbox.exe` est compile avec `console=False` - aucune fenetre console ne s'ouvre, donc aucun risque d'y afficher accidentellement une donnee sensible via `print()`.
- **Signature de code** : `EndpointToolbox.exe` n'est pas signe numeriquement dans cette phase (aucun certificat reel n'existe pour ce projet). Windows SmartScreen avertira au premier lancement - ce n'est pas un contournement de securite, l'utilisateur doit explicitement choisir "Executer quand meme".
- **Build** : `scripts/build_windows.ps1` et `.github/workflows/windows-build.yml` ne contiennent aucun credential, Tenant ID ou Client ID, et n'appellent jamais Microsoft Graph.
