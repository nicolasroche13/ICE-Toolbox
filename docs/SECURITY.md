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

Tenant ID et Client ID sont stockes dans un fichier JSON local.

Le Client Secret est stocke via `keyring` :

- macOS : Keychain si disponible ;
- Windows : Credential Manager si disponible ;
- Linux : backend keyring configure par l'utilisateur.

Si aucun backend securise n'est disponible, Endpoint Toolbox ne sauvegarde pas le secret et affiche une erreur.

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

Le support bundle (`app/intune/support_bundle.py`) passe systematiquement par `app/utils/sanitize.py` avant export. La sanitisation reconnait les cles sensibles en snake_case et en camelCase (`client_secret`/`clientSecret`, `access_token`/`accessToken`, `refresh_token`/`refreshToken`, `id_token`/`idToken`) ainsi que toute cle contenant `authorization`, de maniere recursive dans les dictionnaires, listes et tuples.

## Donnees utilisateur

Les fichiers importes par Deployment Tools ne sont pas conserves apres fermeture hors exports explicitement demandes.

Le Raw Data du Device Inspector contient uniquement le JSON Graph des sources lues pour le device affiche et peut etre exporte volontairement par l'utilisateur. Il est separe par source : Intune Managed Device, Entra Device, Applications et Compliance.

## Read-only Phase 3

Le bouton Refresh relit Microsoft Graph avec des GET. Il ne correspond pas a l'action Intune Sync et ne modifie pas le tenant.

Les echecs partiels sont traites localement :

- 403 sur une source : affichage permission manquante pour la section concernee ;
- 404 sur une source optionnelle : source indisponible ;
- aucune elevation ou permission ReadWrite n'est ajoutee automatiquement.
