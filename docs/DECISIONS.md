# Decisions

## D001 - Application desktop Python

Decision : Python + PySide6.

## D002 - Microsoft Graph strictement read-only

Decision : tous les appels Graph applicatifs passent par `GraphReadOnlyClient`, qui bloque POST, PATCH, PUT et DELETE.

Exception : OAuth2 client credentials utilise POST vers `login.microsoftonline.com` pour obtenir un token. Ce n'est pas une operation Graph sur le tenant.

## D003 - Authentification app-only

Decision : Phase 2 utilise Tenant ID, Client ID et Client Secret avec OAuth2 client credentials.

Raison : pas de connexion utilisateur interactive et modele compatible avec une console d'administration read-only.

## D004 - Secret dans le keychain systeme

Decision : Tenant ID et Client ID peuvent etre stockes dans un JSON local, mais le Client Secret est stocke via `keyring`.

Si aucun backend securise n'est disponible, l'application refuse de sauvegarder le secret.

## D005 - Pas de SDK lourd Graph

Decision : Phase 2 utilise un client HTTP standard base sur `urllib`.

Raison : surface minimale, controle explicite du read-only guard, tests faciles avec transport mocke.

## D006 - Moteurs metier independants de l'UI

Decision : Ring Builder, Graph client et Intune Device Inspector restent testables sans PySide6.

## D007 - Score Representative Pilot simple

Decision : score = `100 - moyenne des ecarts absolus maximum par critere`.

## D008 - Exports non destructifs

Decision : un export ne remplace jamais silencieusement un fichier existant.

## D009 - Device Inspector exception-first

Decision : l'UI Intune met d'abord en avant les anomalies deterministes, puis la conformite, le dernier check-in et les details techniques.

Raison : Endpoint Toolbox doit rendre l'information plus exploitable que le portail, sans pseudo-intelligence.

## D010 - UX progressive disclosure

Decision : l'interface Phase 2.5 n'affiche plus toutes les options simultanement.

Raison : Endpoint Toolbox doit ressembler a un produit desktop technique mais lisible. Les actions frequentes restent immediates, les parametres avances et donnees brutes deviennent secondaires.

## D011 - Composants UI reutilisables

Decision : les composants visuels communs vivent dans `app/ui/components.py` et le style global dans `app/ui/styles.py`.

Raison : eviter la duplication de QSS et conserver une coherence proche du Figma de reference sans reimplementer Qt.

## D012 - Device Health multi-source avec echecs partiels

Decision : le Device Inspector retourne un `DeviceHealth` consolide au lieu de laisser l'UI assembler plusieurs JSON Graph.

Raison : preparer Device Health, Compliance, Applications, Autopilot et Troubleshoot sans coupler l'interface a une seule reponse Graph brute. Une source en 403/404/reseau est representee comme indisponible et n'interrompt pas les sources deja chargees.

## D013 - Compliance transparente

Decision : Phase 3 affiche l'etat `managedDevice.complianceState` et indique que les raisons detaillees ne sont pas disponibles via l'endpoint actuel.

Raison : ne pas inventer de cause de non-conformite. Les details de policy seront ajoutes uniquement avec endpoints et permissions documentes.

## D014 - Application status prudent

Decision : Phase 3 lit les applications detectees et, lorsque disponible, les evenements de troubleshooting applicatif en lecture seule. Les codes erreur sont affiches bruts.

Raison : fournir le point de vue device sans demarrer le monitoring applicatif global ni inventer un decoder d'erreurs.

## D015 - Isolation explicite de l'unique endpoint beta

Decision : `mobileAppTroubleshootingEvents` est le seul appel effectue sur `/beta/` (`GRAPH_BETA_BASE_URL`). Il est isole dans une seule methode avec repli propre ; toute autre source applicative reste sur v1.0.

Raison : v1.0 est prioritaire par principe. Cet endpoint n'a pas d'equivalent v1.0 documente ; l'appeler par erreur sur v1.0 renvoie 404 sur un vrai tenant et cassait silencieusement le statut de deploiement applicatif.

## D016 - Recherche insensible a la casse via tolower()

Decision : les filtres d'egalite Graph (`serialNumber`, `azureADDeviceId`) utilisent `tolower()` cote serveur avec la valeur de recherche normalisee en minuscules. Le filtre `contains(deviceName, ...)` reste inchange (deja insensible a la casse cote Graph).

Raison : un serial number ou un identifiant Entra saisi avec une casse differente de celle stockee dans le tenant ne doit pas produire un resultat de recherche vide.

## D017 - Sanitisation reconnait snake_case et camelCase

Decision : `sanitize_for_export` normalise chaque cle (camelCase et kebab-case vers snake_case) avant de la comparer a la liste des cles sensibles.

Raison : les payloads Graph bruts utilisent camelCase (`clientSecret`, `accessToken`) alors que le code interne utilise snake_case ; une correspondance exacte sur une seule convention laissait passer l'autre.

## D018 - Dates sans fuseau assumees UTC

Decision : `parse_graph_datetime` attache explicitement `timezone.utc` a une date sans indication de fuseau au lieu de laisser Python l'interpreter dans le fuseau local de la machine.

Raison : Microsoft Graph retourne toujours des dates UTC (`Z`) ; une conversion basee sur le fuseau local du poste de l'ingenieur aurait pu fausser silencieusement les calculs de "stale device" selon le fuseau horaire local.

## D019 - Autopilot : modeles et parsers Intune/Entra reutilises tels quels

Decision : `app/autopilot/models.py` importe et reutilise directement `ManagedDevice`, `EntraDevice`, `DeviceIssue`, `SourceStatus`, `Capability`, `HealthStatus` et `CapabilityState` de `app.intune.models` au lieu de creer des types Autopilot dupliques. `app/autopilot/inspector.py` reutilise de meme `parse_managed_device`, `MANAGED_DEVICE_SELECT`, `ENTRA_DEVICE_SELECT`, `_with_source` (`app.intune.device_inspector`) et `parse_entra_device` (`app.intune.health`).

Raison : le modele de capacites, la correlation Entra et la representation d'un managedDevice sont deja corrects et testes depuis la Phase 3.1 ; les dupliquer pour Autopilot aurait cree deux sources de verite a maintenir en parallele sans benefice.

## D020 - Un seul appel beta pour le profil Autopilot, isole comme D015

Decision : seul `GET {beta}/deviceManagement/windowsAutopilotDeviceIdentities/{id}?$expand=deploymentProfile` utilise `/beta/`. Isole dans une seule methode de `AutopilotInspectorService.inspect_device`, avec repli propre (capacite `PERMISSION_MISSING`/`API_UNAVAILABLE`/`ERROR`, jamais d'exception qui casse le reste du diagnostic).

Raison : v1.0 est prioritaire par principe (meme regle que D015). Documentation Microsoft Learn confirmee : la ressource `windowsAutopilotDeviceIdentity` v1.0 n'expose aucune relationship ; `deploymentProfile`, `deploymentProfileAssignmentStatus` et les champs associes n'existent qu'en beta. Il n'y a donc pas d'alternative v1.0 pour obtenir un profil reellement assigne.

## D021 - Priorite a l'identifiant Entra non deprecie pour la correlation Autopilot

Decision : pour correler un appareil Autopilot vers Entra ID, `identity.azure_ad_device_id` (v1.0, documente "to be deprecated") n'est utilise qu'en repli lorsque `managedDevice.azureADDeviceId` (Intune, non deprecie) n'est pas disponible.

Raison : utiliser en priorite un champ que Microsoft documente comme voue a disparaitre aurait rendu la correlation moins fiable a moyen terme sans raison, alors qu'un champ equivalent non deprecie est deja lu par ailleurs (Intune managedDevice).

## D022 - Resolution de recherche Autopilot toujours ramenee au numero de serie

Decision : quel que soit l'identifiant saisi (Autopilot ID, Managed Device ID, Entra Device ID, nom de poste), `AutopilotInspectorService.search_devices` resout d'abord un numero de serie via Intune/Entra puis interroge `windowsAutopilotDeviceIdentities` avec `contains(serialNumber, ...)`.

Raison : `windowsAutopilotDeviceIdentities` ne supporte fiablement que `contains()` sur `serialNumber` en `$filter` (l'operateur `eq` n'est pas fiable sur cet endpoint). Passer par le numero de serie evite de s'appuyer sur un filtre non garanti sur d'autres proprietes de cette ressource.

## D023 - Un appareil resolu hors Autopilot reste visible comme "non enregistre"

Decision : lorsque la recherche resout un appareil via Intune ou Entra mais qu'aucun enregistrement Autopilot ne correspond a son numero de serie, `search_devices` renvoie tout de meme un `AutopilotSearchResult` avec `id=""`, et `inspect_device` construit un `AutopilotDeviceHealth` avec une identite vide plutot que d'echouer.

Raison : "savoir si un appareil est enregistre dans Autopilot" fait partie de la definition de fait de ce module (item 3, Phase 4). Sans cette decision, l'absence de resultat Autopilot serait indiscernable d'une recherche qui n'a simplement rien trouve.
