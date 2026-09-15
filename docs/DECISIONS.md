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

## D024 - alternativeSecurityIds et physicalIds jamais lus

Decision : `app/entra/inspector.py` ne selectionne jamais `alternativeSecurityIds` ni `physicalIds` sur la ressource `device`, et `EntraDeviceDetail` ne les modelise pas.

Raison : Microsoft documente ces deux proprietes comme "For internal use only" sur la ressource `device` v1.0. Aucune valeur diagnostique n'a ete identifiee pour le troubleshooting device, et les exposer (y compris dans Raw Data) serait une exposition sans benefice demontre. Coherent avec la consigne Phase 5 de ne les inclure que si "reellement utile" - ce n'est pas le cas ici.

## D025 - Correlation Autopilot depuis Entra reutilise search_devices, jamais l'appel beta

Decision : la correlation Autopilot de `EntraInspectorService.inspect_device` appelle `AutopilotInspectorService.search_devices(serial)` (identite Autopilot de base uniquement) et n'appelle jamais `inspect_device` d'Autopilot, donc jamais l'endpoint beta `$expand=deploymentProfile`.

Raison : la page Entra ID doit rester centree sur Entra ID et afficher une correlation utile sans dupliquer toute la page Autopilot (consigne UI explicite). Appeler le profil beta depuis la page Entra aurait ajoute un appel Graph (et une dependance beta) non demande par cette page ; l'utilisateur qui a besoin du profil peut ouvrir la page Autopilot directement.

## D026 - Pas de regle "os_version_mismatch" entre Entra et Intune

Decision : Endpoint Toolbox n'implemente pas de regle Health comparant `device.operatingSystemVersion` (Entra) et `managedDevice.osVersion` (Intune), contrairement a `identifier_mismatch` (Phase 4) qui compare des identifiants.

Raison : Entra ID et Intune synchronisent leurs proprietes a des rythmes independants ; une difference de version OS entre les deux est un artefact courant et attendu du delai de synchronisation, pas un signal fiable d'anomalie. Contrairement a `identifier_mismatch` (ou le risque de faux positif n'a ete identifie qu'apres coup, voir Limitations Phase 4), ce risque etait connu des la conception de Phase 5 ; la consigne explicite ("eviter les faux positifs connus") justifie de ne pas creer cette regle plutot que de la creer puis la corriger. Les deux valeurs restent visibles cote a cote en Raw Data/Diagnostics.

## D027 - Seuil de staleness Entra distinct du seuil Intune

Decision : `entra_device_stale` utilise une constante dediee `ENTRA_STALE_SIGN_IN_DAYS = 90` dans `app/entra/health.py`, non liee au reglage "Seuil stale device" des Settings (qui reste specifique a `managedDevice.lastSyncDateTime`, Intune).

Raison : `approximateLastSignInDateTime` (Entra, activite de connexion interactive) et `lastSyncDateTime` (Intune, cycle de check-in MDM ~8h automatique) mesurent des activites de nature differente et ne progressent pas au meme rythme. Reutiliser le seuil de 7 jours deja configure pour Intune aurait produit un volume important de faux "stale" sur des appareils actifs mais sans reconnexion interactive recente. 90 jours correspond a l'ordre de grandeur communement cite par Microsoft pour le nettoyage des appareils Entra ID inactifs.

## D028 - Device Workspace compose les trois services existants, jamais un quatrieme moteur de diagnostic

Decision : `DeviceWorkspaceService` ne contient aucune regle Health, aucun parsing Graph et aucun modele de donnees "source" propre. Il ne fait que composer `IntuneDeviceInspectorService`, `AutopilotInspectorService` et `EntraInspectorService` deja existants, et projeter leurs resultats dans des dataclasses de presentation (`AutopilotBlock`, `EntraBlock`, `IntuneBlock`, `DeviceWorkspaceResult`).

Raison : la meme raison que D019 (reutiliser plutot que dupliquer), appliquee une troisieme fois. Un quatrieme moteur de diagnostic parallele aurait double la surface de maintenance des regles Health (deja 10 + 5 dans Autopilot/Entra) sans aucun benefice : chaque module specialise sait deja calculer son propre statut, ses propres issues et ses propres capacites correctement. La consigne explicite de la Phase 6 ("sans creer un moteur de diagnostic parallele, sans dupliquer les regles metier deja existantes") a ete respectee au sens strict : aucune fonction du Workspace ne reimplemente une regle deja presente dans `app/intune/health.py`, `app/autopilot/health.py` ou `app/entra/health.py`.

## D029 - Ordre de resolution d'identite fixe et documente, jamais heuristique

Decision : pour un identifiant de type GUID, l'ordre d'ancrage est **Intune -> Autopilot -> Entra** (le premier service qui retourne exactement un candidat gagne). Pour une recherche texte (numero de serie ou nom), l'ordre est **Autopilot (recherche serial) -> Intune (fallback nom)** ; le Workspace n'appelle jamais `EntraInspectorService.search_devices` directement pour une recherche texte (Entra ne supporte que l'egalite exacte sur `displayName`, deja atteignable via la resolution GUID si necessaire).

Raison : un ordre fixe et documente est deterministe et auditable, contrairement a une heuristique qui choisirait "le service qui semble le plus complet". L'ordre GUID reflete la richesse de dispatch interne de chaque service (Autopilot sait deja resoudre un Managed Device ID ou un Entra Device ID vers son identite propre par correlation inverse) ; l'ordre texte reflete un fait decouvert en concevant Phase 6 : la recherche par nom interne d'Autopilot (`_search_by_device_name`) ignore silencieusement les devices Intune-only (voir D030), donc l'appel Intune direct en repli est necessaire pour ne pas perdre de resultats.

## D030 - Le Workspace n'appelle jamais `_search_by_device_name` d'Autopilot pour une recherche texte generale

Decision : `DeviceWorkspaceService._search_text` appelle `AutopilotInspectorService.search_devices` uniquement avec un numero de serie candidat (jamais avec un nom de poste), et appelle separement `IntuneDeviceInspectorService.search_devices` avec le nom de poste en repli.

Raison : `AutopilotInspectorService._search_by_device_name` fait le pont vers Intune (`managedDevices?$filter=contains(deviceName, ...)`) puis prend le `serialNumber` du managedDevice trouve pour chercher dans Autopilot - mais si le managedDevice n'a pas de correspondance Autopilot, ce pont retourne un resultat vide plutot qu'un candidat "Intune-only" (contrairement a ses methodes de pont par GUID, qui elles synthetisent un candidat "non enregistre" - voir D023). Reutiliser ce pont depuis le Workspace pour une recherche generale par nom aurait donc silencieusement perdu tous les devices geres par Intune mais jamais inscrits dans Autopilot. Appeler Intune directement en repli evite cette perte sans modifier le comportement de la page Autopilot elle-meme (qui garde son comportement existant, inchange). Voir aussi Limitations Phase 6 dans `docs/GRAPH_PERMISSIONS.md`.

## D031 - Detection de conflit d'identifiants (`IdentityConflict`) : presentation uniquement, ne remplace pas `identifier_mismatch`

Decision : `ResolvedIdentity.conflicts` (Phase 6) signale une incoherence de *valeur* entre deux sources pour le meme type d'identifiant (ex. deux numeros de serie differents rapportes par Autopilot et par Intune) a des fins d'affichage uniquement (badge dans la carte identite). Cela ne cree ni ne modifie une `DeviceIssue`, et ne remplace pas la regle `identifier_mismatch` d'Autopilot (`app/autopilot/health.py`), qui reste la seule source de verite pour la severite d'une incoherence d'identifiant.

Raison : la consigne Phase 6 est explicite ("cette detection de conflit ne doit pas remplacer `identifier_mismatch`"). Les deux mecanismes repondent a des besoins differents : `identifier_mismatch` est une regle Health avec une severite deliberement choisie (voir Limitations Phase 4 sur le risque de faux positif deja connu), evaluee par le module qui possede le contexte metier complet (Autopilot) ; `IdentityConflict` est une aide de presentation generique au niveau du Workspace, utile meme quand aucun module specialise n'a pu evaluer `identifier_mismatch` (par exemple si l'ancrage est Entra et qu'Autopilot n'a jamais ete interroge en profondeur). Fusionner les deux aurait couple la logique de presentation du Workspace a la logique de severite d'un module specialise, violant la couche d'orchestration pure visee par D028.

## D032 - Aucun appel Graph d'enrichissement supplementaire dans les blocs de synthese Workspace

Decision : les blocs `AutopilotBlock`, `EntraBlock` et `IntuneBlock` affichent un niveau de detail asymetrique selon le service ayant servi d'ancrage (ex. un ancrage Autopilot donne un profil de deploiement complet mais un bloc Entra allege ; un ancrage Entra donne l'inverse) plutot que d'emettre des appels Graph additionnels pour "completer" les blocs les moins riches.

Raison : consigne explicite de la Phase 6 ("N'ajoute pas de nouveaux appels Graph pour enrichir ces cartes"). Completer systematiquement chaque bloc au niveau de detail maximal aurait multiplie le nombre d'appels Graph par recherche (jusqu'a un appel beta supplementaire pour le profil Autopilot a chaque fois), ce qui contredit la discipline de performance demandee (reutiliser les objets deja recuperes, jamais dupliquer un appel). L'asymetrie est un compromis assume : l'utilisateur qui a besoin du detail manquant peut l'obtenir en un clic via le lien "Ouvrir dans <module>" (qui reutilise l'identifiant deja resolu, sans nouvelle saisie).

## D033 - PyInstaller sans alternative serieuse envisagee

Decision : le packaging Windows (Phase 7) utilise PyInstoller (onefile, `console=False`), configure via `packaging/windows/EndpointToolbox.spec`.

Raison : deja largement utilise pour des applications PySide6/Qt desktop, avec des hooks officiels integres pour PySide6 et, via `pyinstaller-hooks-contrib`, des hooks communautaires pour pandas/openpyxl (evite d'ecrire et maintenir des `hiddenimports` manuels pour des bibliotheques volumineuses). Aucune incompatibilite avec ce projet n'a ete identifiee lors du build structurel effectue sur macOS (voir `docs/PACKAGING.md`, "Build reellement effectue") : la consigne explicite etait de choisir PyInstoller "sauf incompatibilite demontree", et aucune ne l'a ete.

## D034 - Nouveau module `app/core/paths.py`, seul point de contact avec `sys.frozen`/`sys._MEIPASS`

Decision : toute resolution de chemin dependant du mode d'execution (developpement vs execute par PyInstoller) passe par `app/core/paths.py` (`is_frozen`, `frozen_resource_root`, `resource_path`, `user_data_dir`, `user_log_dir`). Aucun autre fichier du projet ne lit `sys.frozen` ou `sys._MEIPASS` directement.

Raison : consigne explicite de la Phase 7 ("Ne disperse pas `sys._MEIPASS` partout dans le code"). Centraliser ce mecanisme signifie qu'ajouter une future ressource embarquee (icone, template) ou changer de strategie PyInstoller (onefile vers onedir, par exemple) ne necessite de modifier qu'un seul fichier plutot que de retrouver chaque site d'appel disperse.

## D035 - `GraphConfigStore` utilise `user_data_dir()`, macOS/Linux inchanges, Windows sur `%APPDATA%`

Decision : `app/graph/config.py` calcule desormais `CONFIG_DIR` via `app.core.paths.user_data_dir()` au lieu d'un `Path.home() / ".endpoint_toolbox"` code en dur. La fonction retourne `%APPDATA%\EndpointToolbox` sur Windows (repli `~\AppData\Roaming\EndpointToolbox` si `APPDATA` est absent de l'environnement) et conserve `~/.endpoint_toolbox` a l'identique sur macOS et Linux.

Raison : consigne explicite ("Preferer `%APPDATA%\EndpointToolbox\`... Preserver le fonctionnement macOS/Linux existant si possible"). Le format du fichier JSON et son contenu (Tenant ID, Client ID, seuil stale device - jamais le Client Secret) restent inchanges ; seul l'emplacement racine change, et uniquement sur Windows. `GraphConfigStore` continue d'accepter un `Path` explicite en parametre (deja le cas avant cette phase), donc aucun test existant n'a eu besoin d'etre modifie.

## D036 - Filet de securite `app/core/logging_setup.py` : infrastructure, pas une fonctionnalite

Decision : introduction d'un `RotatingFileHandler` minimal (fichier unique `endpoint_toolbox.log`, 1 Mo x 3, sous `user_log_dir()`) et d'un `sys.excepthook` qui journalise toute exception non interceptee, active des le demarrage par `main.py`. Aucune journalisation des appels Graph, aucune donnee applicative, aucun secret n'y transite.

Raison : `EndpointToolbox.exe` est compile avec `console=False` (consigne explicite "aucune fenetre console visible") - sans ce filet, un crash au demarrage sur le poste d'un utilisateur serait invisible et impossible a diagnostiquer a distance, ce qui aurait rendu la Phase 7 incomplete au sens pratique. Ce n'est pas une fonctionnalite metier (aucune regle Intune/Autopilot/Entra/Workspace n'y touche, aucun appel Graph n'y transite) : c'est une infrastructure de packaging, au meme titre que `app/core/paths.py`. Perimetre volontairement minimal : pas de rotation configurable, pas de niveau de log ajustable par l'utilisateur, pas de journalisation des appels Graph (deja couverts par les Diagnostics in-app existants).

## D037 - `app/version.py` comme source unique de version, distincte des marqueurs `APP_VERSION` des Support Bundle

Decision : nouveau fichier `app/version.py` (`__version__ = "0.7.0"`), utilise uniquement pour les metadonnees de l'executable Windows (`packaging/windows/version_info.txt`). Les constantes `APP_VERSION = "phase-N"` deja presentes dans `app/intune/support_bundle.py`, `app/autopilot/support_bundle.py`, `app/entra/support_bundle.py` et `app/workspace/support_bundle.py` ne sont pas modifiees.

Raison : consigne explicite ("Ajouter une gestion propre de version si elle n'existe pas"). Une version applicative unifiee et les marqueurs de phase par module repondent a des besoins differents : la premiere identifie l'executable distribue, les seconds identifient quel module a produit un Support Bundle donne (utile pour le support technique, sans rapport avec le packaging). Les fusionner aurait couple deux concepts independants et oblige a modifier quatre fichiers metier pour une tache de packaging pure - contraire a la consigne "ne modifie pas les regles Intune/Autopilot/Entra/Workspace".

## D038 - Aucune icone inventee ; mecanisme d'ajout prepare uniquement

Decision : `packaging/windows/EndpointToolbox.spec` verifie la presence de `resources/windows/app.ico` a la compilation (`Path.exists()`) et l'attache a l'executable seulement si le fichier existe reellement dans le depot ; en son absence, l'executable est compile avec l'icone par defaut de PyInstoller.

Raison : consigne explicite ("Si une icone existe reellement, l'utiliser. Sinon ne genere pas arbitrairement une identite visuelle definitive"). Aucune icone Endpoint Toolbox n'existe dans ce depot a ce jour ; en creer une aurait fixe une identite visuelle non demandee et potentiellement a refaire.

## D039 - Pas de signature de code dans la Phase 7

Decision : `EndpointToolbox.exe` n'est pas signe numeriquement en Phase 7. `docs/PACKAGING.md` documente explicitement que Windows SmartScreen avertira au premier lancement.

Raison : consigne explicite ("Ne signe pas numeriquement l'executable dans cette phase si aucun certificat de signature n'existe"). Aucun certificat de signature de code n'existe pour ce projet a ce moment ; signer sans certificat reel est impossible, et en simuler un aurait ete une invention masquant une limitation reelle a l'utilisateur. **Superseded en partie par D040-D043 (Phase 7.2)** : l'infrastructure de signature optionnelle existe desormais, mais reste inactive par defaut - le raisonnement de D039 (ne jamais pretendre signer sans certificat reel) continue de s'appliquer telle quelle.

## D040 - Signature Authenticode strictement optionnelle, jamais requise pour builder

Decision : `scripts/build_windows.ps1` et `.github/workflows/windows-build.yml` produisent un `EndpointToolbox.exe` non signe par defaut. La signature ne se declenche que si `CODESIGN_THUMBPRINT` (variable d'environnement locale, ou variable de depot GitHub Actions `vars.CODESIGN_THUMBPRINT`) est explicitement definie.

Raison : consigne explicite Phase 7.2 ("Un developpeur sans certificat doit toujours pouvoir compiler EndpointToolbox.exe"). Rendre la signature obligatoire aurait bloque tout contributeur sans certificat de signature - or aucun certificat reel (test ou public) n'est garanti disponible pour quiconque reprend ce depot.

## D041 - Thumbprint en parametre explicite, jamais code en dur ; aucune URL de timestamp inventee

Decision : `scripts/sign_windows.ps1` exige `-CertificateThumbprint` en parametre obligatoire (aucune valeur par defaut, aucun thumbprint litteral nulle part dans le code ou la documentation) et accepte `-TimestampUrl` en parametre optionnel sans URL par defaut.

Raison : consigne explicite ("Le thumbprint ne doit pas etre code en dur" ; "IMPORTANT : ne pas inventer d'URL de serveur de timestamp"). Un thumbprint code en dur aurait suppose un certificat specifique n'existant potentiellement pas sur la machine du lecteur ; inventer une URL de timestamp aurait pu orienter silencieusement vers un service non choisi ou non approuve par l'utilisateur/le fournisseur reel du certificat.

## D042 - Etape de signature GitHub Actions conditionnee a une variable, jamais a un secret PFX

Decision : la nouvelle etape "Sign EndpointToolbox.exe" de `windows-build.yml` est gardee par `if: ${{ vars.CODESIGN_THUMBPRINT != '' }}` - une variable de depot/organisation GitHub Actions (non confidentielle), jamais un `secrets.*`. Aucun fichier PFX, mot de passe, cle privee ou credential de service de signature n'est ajoute au workflow ou au depot.

Raison : consigne explicite ("Ne mets JAMAIS dans le repository : fichier PFX reel ; clé privee ; mot de passe PFX..." et "ne cree pas une architecture fragile consistant a stocker durablement une cle privee exportee dans le repository"). Un thumbprint identifie un certificat sans exposer de materiel cryptographique : ce n'est pas un secret, donc une variable simple est le bon niveau de confidentialite. Ce mecanisme est concu pour un runner self-hosted dont le magasin de certificats local detient deja le certificat ; sur le runner `windows-latest` heberge par GitHub (ephemere), l'activer sans un tel runner ferait simplement echouer l'etape (certificat introuvable) - un echec explicite plutot qu'une degradation silencieuse ou un contournement via un PFX importe a chaque run.

## D043 - Scripts de signature ne modifient jamais Trusted Root/Trusted Publishers

Decision : ni `scripts/create_test_codesigning_cert.ps1`, ni `scripts/sign_windows.ps1`, ni `scripts/verify_windows_signature.ps1` ne touchent aux magasins `Cert:\CurrentUser\Root`, `Cert:\LocalMachine\Root` ou Trusted Publishers - verifie explicitement par `tests/test_code_signing_structure.py::test_codesigning_scripts_never_touch_trusted_root_or_publisher_stores`.

Raison : consigne explicite ("IMPORTANT : ne modifie pas automatiquement les Trusted Publishers/Trusted Root stores. Ne cree pas de script qui deploie silencieusement un certificat de confiance"). Etablir une confiance machine par machine est une decision de securite qui doit rester un acte deliberement pris par un administrateur (voir `docs/CODE_SIGNING.md`, section 11), jamais un effet de bord silencieux d'un script de build ou de signature.
