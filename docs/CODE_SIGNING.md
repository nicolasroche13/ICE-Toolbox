# Code Signing Windows (Phase 7.2)

Reference technique de la signature Authenticode optionnelle d'`EndpointToolbox.exe`.
Cette phase ne modifie aucune fonctionnalite metier, aucune regle Intune/Autopilot/
Entra/Workspace, aucune permission Graph. Voir `docs/ROADMAP.md` (Phase 7.2) et
`NEXT.md` pour le statut exact.

## 1. Pourquoi signer

Un executable Windows non signe n'a aucune identite d'editeur verifiable : Windows
ne peut pas garantir qui l'a produit ni qu'il n'a pas ete modifie apres compilation.
Signer `EndpointToolbox.exe` avec Authenticode permet a Windows (et a l'utilisateur,
via les proprietes du fichier) de verifier l'origine et l'integrite du binaire, et
peut ameliorer le comportement de SmartScreen dans certains environnements (voir
section 7).

## 2. Ce qu'Authenticode garantit

- **Integrite** : le fichier n'a pas ete modifie depuis sa signature (toute
  modification, meme d'un octet, invalide la signature - voir section 9,
  "Ordre important").
- **Identite du signataire** : le certificat utilise identifie qui a signe, avec
  une chaine de confiance verifiable jusqu'a une autorite de certification (CA) si
  le certificat est reconnu.
- **Horodatage** (si un timestamp RFC 3161 est applique) : preuve que la signature
  a ete produite a un instant donne, independamment de la duree de validite
  ulterieure du certificat (voir section 8).

## 3. Ce qu'Authenticode ne garantit PAS

- **Pas une garantie de securite du contenu** : un binaire signe peut toujours
  contenir un bug ou, en theorie, du code malveillant si le signataire lui-meme
  est compromis ou malveillant. La signature identifie l'editeur, elle ne certifie
  pas la qualite ou l'innocuite du code.
- **Pas une suppression automatique des avertissements SmartScreen** : voir
  section 7 - un certificat, meme public et reconnu, n'elimine pas
  systematiquement un avertissement SmartScreen, notamment pour un executable
  recemment publie sans reputation etablie.
- **Pas une preuve de confiance publique pour un certificat auto-signe ou
  interne** : voir sections 4 et 5 - seule une chaine de confiance reconnue par
  la machine qui verifie la signature produit un resultat "de confiance".

## 4. Certificat auto-signe (MODE 1 - TEST)

Cree via `scripts/create_test_codesigning_cert.ps1` (voir section 9). Usage
strictement limite au developpement, aux machines personnelles, ou a un
environnement interne ou le certificat racine/editeur a ete **explicitement**
approuve (voir section 11).

**Ne jamais presenter ce certificat comme une solution de confiance publique.**
Sur une machine externe qui ne fait pas confiance au certificat, Windows ne
considerera pas automatiquement l'editeur comme fiable : `Get-AuthenticodeSignature`
et `signtool verify` signaleront une chaine de confiance non reconnue
(`NotTrusted` / "A certificate chain could not be built to a trusted root
authority"), meme si la signature elle-meme est techniquement valide (fichier non
modifie, cle privee correcte).

Le script `create_test_codesigning_cert.ps1` :

- cree un certificat Code Signing SHA-256 dans `Cert:\CurrentUser\My` (aucun droit
  administrateur requis) ;
- utilise un `Subject` explicitement marque `TEST` / `DO NOT TRUST` - jamais un nom
  pretendant etre Microsoft ou une entreprise tierce ;
- affiche le thumbprint du certificat cree ;
- explique ou il est stocke ;
- **n'exporte jamais la cle privee** - elle reste dans le magasin de certificats
  Windows, protegee par le profil utilisateur Windows ;
- **ne modifie jamais** les magasins Trusted Root/Trusted Publishers (voir
  section 11).

## 5. Certificat interne (entreprise)

Un certificat Code Signing emis par une autorite de certification interne
d'entreprise (PKI d'entreprise) fonctionne avec exactement les memes scripts
(`sign_windows.ps1`, `verify_windows_signature.ps1`) : seul le thumbprint change,
jamais le code. Sur les postes geres ou la chaine de confiance de cette CA interne
est deja approuvee (typiquement via GPO ou une solution de gestion des postes),
l'editeur devient verifiable et le comportement est nettement meilleur que pour un
certificat auto-signe non deploye (voir section 7, cas 3). Cette phase ne met en
place ni CA interne ni distribution de confiance - voir section 11.

## 6. Certificat public (MODE 3 - futur)

**Aucun fournisseur n'est choisi ni achete dans cette phase.** Familles possibles a
evaluer plus tard, sans aucun engagement ici :

- **Certificat Code Signing public** delivre par une autorite de certification
  (CA) publiquement reconnue par Windows (liste de confiance racine Microsoft).
- **Service de signature cloud compatible Authenticode** (HSM cloud) : la cle
  privee ne quitte jamais un module materiel securise gere par le fournisseur ;
  la signature se fait via une API/CLI plutot qu'un fichier PFX local.
- **Infrastructure de signature d'entreprise** (HSM on-premise, serveur de
  signature centralise) : meme principe, cle privee jamais exportee, signature
  demandee via un service interne.

L'architecture de `sign_windows.ps1` (parametre `-CertificateThumbprint`, jamais
code en dur) permet de remplacer un certificat de test par un certificat public
**sans modifier le code d'Endpoint Toolbox** - seul le thumbprint (et
eventuellement le mecanisme d'acces a la cle, si un HSM/service cloud est utilise
a la place du magasin de certificats local) change.

**Un certificat public standard n'elimine pas systematiquement SmartScreen** - voir
section 7, cas 4.

## 7. SmartScreen : les quatre cas

| # | Situation | Consequence |
| --- | --- | --- |
| 1 | EXE **non signe** | Integrite et editeur non authentifies. Avertissements Windows/SmartScreen possibles, notamment via le marqueur "telecharge depuis Internet" (Mark of the Web). |
| 2 | EXE signe avec un **certificat auto-signe non approuve** sur le poste | Signature techniquement presente (integrite verifiable), mais chaine de confiance non reconnue. Avertissements toujours possibles - la signature seule ne suffit pas. |
| 3 | EXE signe avec un **certificat interne dont la chaine est approuvee** sur les postes geres | Editeur verifiable dans cet environnement precis. Comportement nettement meilleur sur le parc gere ou la confiance a ete explicitement etablie (section 11). |
| 4 | EXE signe avec un **certificat public reconnu** | Editeur authentifie publiquement. Meilleure base pour la reputation SmartScreen (base sur l'identite verifiee et l'historique de publication), **mais aucun engagement que SmartScreen n'affichera jamais d'avertissement** - la reputation de fichier/reputation d'editeur SmartScreen est aussi fonction du volume de telechargements et de l'anciennete, pas uniquement de la signature. |

**Aucun contournement SmartScreen n'est developpe ici.** Cette phase ne desactive
jamais Defender ou SmartScreen, et ne cherche a modifier aucune protection Windows.

## 8. Timestamp (RFC 3161)

Un timestamp RFC 3161 permet a une signature valide de rester verifiable **apres
l'expiration du certificat de signature**, selon les regles Authenticode standard :
la verification se fonde alors sur l'instant horodate (prouve par une autorite de
timestamp tierce) plutot que sur la date de verification courante.

**Aucune URL de serveur de timestamp n'est codee en dur dans ce depot.**
`scripts/sign_windows.ps1` accepte `-TimestampUrl` en parametre optionnel, sans
valeur par defaut. Pour signer avec timestamp, fournir l'URL du serveur de
timestamp du fournisseur reel du certificat utilise, ou d'une autorite de
timestamp explicitement choisie par vous - jamais une URL devinee ou inventee par
cet agent. Signer sans `-TimestampUrl` reste possible ; la signature sera alors
soumise a l'expiration du certificat comme decrit ci-dessus.

## 9. Procedure de signature

Ordre strict, imperatif : **la signature doit etre la DERNIERE modification du
binaire**. Ne jamais signer avant l'execution de PyInstaller (`packaging/windows/
EndpointToolbox.spec`), et ne jamais modifier `EndpointToolbox.exe` apres
signature - toute modification post-signature invalide la signature.

1. **(Une fois, developpement/test uniquement)** Creer un certificat de test :
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\create_test_codesigning_cert.ps1
   ```
   Note le thumbprint affiche.
2. Construire l'executable normalement :
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
   ```
3. Signer (etape separee, explicite) :
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\sign_windows.ps1 `
     -Path dist\EndpointToolbox.exe `
     -CertificateThumbprint <thumbprint> `
     -TimestampUrl <url-si-disponible>
   ```
   Ou, de maniere integree (signature automatique en derniere etape du build) :
   ```powershell
   $env:CODESIGN_THUMBPRINT = "<thumbprint>"
   $env:CODESIGN_TIMESTAMP_URL = "<url-si-disponible>"   # optionnel
   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
   ```
   Sans `CODESIGN_THUMBPRINT`, `build_windows.ps1` produit un executable **non
   signe**, exactement comme avant cette phase - un certificat n'est jamais requis
   pour compiler.

`sign_windows.ps1` verifie lui-meme la signature immediatement apres l'avoir
appliquee (voir section 10) et echoue avec un code de sortie non nul si cette
verification ne rapporte pas un resultat `Valid`.

## 10. Procedure de verification

Deux outils complementaires, tous deux utilises par `scripts/verify_windows_signature.ps1` :

```powershell
Get-AuthenticodeSignature .\dist\EndpointToolbox.exe
```

```powershell
signtool verify /pa /v dist\EndpointToolbox.exe
```

`scripts/verify_windows_signature.ps1 -Path dist\EndpointToolbox.exe` execute les
deux et classe le resultat sans ambiguite :

- **UNSIGNED** - `Get-AuthenticodeSignature` retourne `NotSigned`.
- **VALID** - signature verifiee, chaine de confiance etablie, fichier non modifie.
- **INVALID** - `HashMismatch` (le fichier a ete modifie apres signature) ou autre
  echec de verification.
- **UNKNOWN/UNTRUSTED CERTIFICATE** - `NotTrusted` : signature techniquement
  presente mais la chaine de confiance n'est pas reconnue sur cette machine
  (cas typique d'un certificat de test, section 4).
- **EXPIRED** (note distincte) - le certificat a expire ET aucun timestamp n'est
  present : la signature est alors traitee comme non valide selon les regles
  Authenticode (voir section 8).

## 11. Stockage securise de la cle privee

- **Mode 1/2 (test, local)** : la cle privee reste dans le magasin de certificats
  Windows (`Cert:\CurrentUser\My`), protegee par le profil utilisateur Windows.
  Jamais exportee automatiquement par `create_test_codesigning_cert.ps1`.
- **Mode 3 (futur, public/entreprise)** : privilegier, des que possible, une
  solution ou la cle privee **ne quitte jamais** un environnement protege :
  Certificate Store protege (materiel type TPM/carte a puce), HSM, service cloud
  de signature, infrastructure de signature d'entreprise. `sign_windows.ps1`
  n'exige qu'un thumbprint resolu localement par le magasin de certificats - ce
  meme script fonctionnerait avec un certificat expose par un fournisseur HSM/cloud
  via un CSP/KSP Windows, sans modification.

## 12. GitHub Actions

`.github/workflows/windows-build.yml` fonctionne **sans aucune modification de
comportement par defaut** : la nouvelle etape "Sign EndpointToolbox.exe" est
conditionnee a `vars.CODESIGN_THUMBPRINT != ''` (une variable de depot/organisation
GitHub Actions - **pas** un secret, un thumbprint n'etant pas confidentiel). Cette
variable n'existe pas aujourd'hui : l'etape est un no-op, le workflow produit
l'executable non signe exactement comme avant.

**Jamais dans ce depot** : fichier PFX reel, cle privee, mot de passe PFX, PIN,
credential de service de signature, certificat prive encode en base64 dans un
YAML, ou token de fournisseur de signature. Aucun de ces elements n'a ete ajoute.

Ce mecanisme conditionnel est concu pour un **runner Windows self-hosted** dont le
magasin de certificats local contient deja le certificat de signature - le
thumbprint seul (non confidentiel) suffit alors a l'identifier. Sur le runner
`windows-latest` heberge par GitHub (ephemere, sans magasin de certificats
persistant), activer cette variable sans un tel runner self-hosted ferait echouer
l'etape de signature (certificat introuvable) - c'est le comportement attendu, pas
une degradation silencieuse.

**Ne pas construire une architecture fragile** consistant a stocker durablement une
cle privee exportee (PFX) dans les secrets GitHub Actions et a l'importer a chaque
run : cela expose la cle privee en clair dans la memoire de chaque execution CI
ephemere. La voie recommandee a terme, si une signature automatisee en CI est
souhaitee, est l'une de : runner self-hosted avec Certificate Store/HSM local,
service cloud de signature avec authentification federee (pas de secret
long-lived stocke), ou infrastructure de signature d'entreprise appelee via une
API. Aucun de ces services n'est configure dans cette phase.

## 13. Procedure future pour certificat public

Quand un certificat public sera obtenu (hors perimetre de cette phase - aucun
fournisseur n'est choisi ni achete ici) :

1. Importer le certificat (et sa cle privee, selon le mode de livraison du
   fournisseur - fichier PFX protege, HSM, ou service cloud) dans un magasin ou un
   mecanisme d'acces compatible `signtool`/CSP Windows.
2. Noter son thumbprint.
3. Utiliser exactement les memes commandes que la section 9, en remplacant le
   thumbprint de test par celui du certificat public, et en fournissant l'URL de
   timestamp reelle du fournisseur du certificat (jamais une URL devinee).
4. Aucune modification du code Endpoint Toolbox, de `sign_windows.ps1` ou de
   `verify_windows_signature.ps1` n'est necessaire.

## 14. Rotation / expiration du certificat

- Verifier `NotAfter` du certificat (`(Get-ChildItem Cert:\CurrentUser\My\<thumbprint>).NotAfter`)
  avant chaque campagne de signature.
- Un binaire deja signe **avec** un timestamp RFC 3161 reste verifiable apres
  l'expiration du certificat de signature (section 8) - inutile de re-signer les
  builds passes.
- Un binaire signe **sans** timestamp devient invalide des l'expiration du
  certificat - tout nouveau build necessite alors un certificat non expire.
- Lors du renouvellement d'un certificat (test, interne ou public), seul le
  thumbprint fourni a `sign_windows.ps1` (ou a la variable `CODESIGN_THUMBPRINT`)
  change - aucune modification de script ou de workflow n'est necessaire.
- Un certificat de test cree par `create_test_codesigning_cert.ps1` expire apres 1
  an (`-NotAfter (Get-Date).AddYears(1)`) ; re-executer le script pour en creer un
  nouveau le moment venu.

## Etat reel de cette phase (voir aussi NEXT.md)

- Infrastructure de signature (scripts, integration build, workflow) :
  **preparee et validee par une signature de TEST reelle**.

### Signature de TEST reellement effectuee le 2026-09-15 (GitHub Actions `windows-latest`)

Via le workflow `windows-codesign-validate.yml` (repo `nicolasroche13/ICE-Toolbox`,
run 35011776362), sur un `EndpointToolbox.exe` reellement construit par
PyInstoller dans le meme run :

| Element | Valeur reelle observee |
| --- | --- |
| signtool localise | `C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe` |
| Certificat cree | `create_test_codesigning_cert.ps1`, reussi |
| Subject | `CN=Endpoint Toolbox TEST Code Signing - DO NOT TRUST, O=Endpoint Toolbox development (not a real company), OU=TEST CERTIFICATE - NOT FOR PRODUCTION USE` |
| Thumbprint | `4E19DC35D08C007530E78CA9AFA7EDA3FB91156F` |
| Expiration certificat | 15 septembre 2027 |
| Algorithme de hachage du fichier | SHA-256 confirme par signtool (`Hash of file (sha256): 2715597F8AA6CEB144A910C6B0961FD44A92058A9BA2C2F36BEEA6713D403DA0`) |
| Timestamp | **Aucun** - `-TimestampUrl` non fourni (aucune URL inventee), signtool confirme `File is not timestamped.` |
| `signtool sign` | Reussi (`Successfully signed: ...EndpointToolbox.exe`) |
| **Avant** confiance explicite - `signtool verify /pa /v` | **Echec** (1 erreur) : `SignTool Error: A certificate chain processed, but terminated in a root certificate which is not trusted by the trust provider.` |
| **Avant** confiance explicite - `Get-AuthenticodeSignature` | `Status: UnknownError`, `StatusMessage: A certificate chain processed, but terminated in a root certificate which is not trusted by the trust provider.` |
| **Avant** confiance explicite - `sign_windows.ps1` | **Sort avec le code 1**, exactement comme concu (etape 9 : echouer si la verification finale n'est pas `Valid`) |
| **Avant** confiance explicite - `verify_windows_signature.ps1` | Classification **`INVALID/UNKNOWN`**, code de sortie 1 |
| Etape de confiance CI (demonstration uniquement) | `certutil.exe -addstore -f Root` sur ce runner ephemere - `CertUtil: -addstore command completed successfully.` |
| **Apres** confiance explicite (demonstration CI uniquement) - `verify_windows_signature.ps1` | Classification **`VALID`**, code de sortie **0** |
| **Apres** confiance explicite - `Get-AuthenticodeSignature` | `Status: Valid` |

**Lecture de ce resultat** : ce test confirme exactement le cas 2 documente en
section 7 (certificat auto-signe non approuve -> signature techniquement
presente, chaine de confiance non reconnue, `sign_windows.ps1` refuse
correctement de considerer cela comme un succes) puis, une fois la confiance
explicitement etablie sur cette meme machine ephemere (jamais fait par les
scripts livres eux-memes - action manuelle et clairement etiquetee de ce
workflow de validation uniquement), le cas 3 (chaine de confiance reconnue ->
`Valid`). Aucune valeur de confiance publique n'est demontree par ce test : le
certificat reste un certificat de TEST auto-signe, non approuve par defaut sur
toute autre machine.

Une premiere tentative (run 35010803489) s'est bloquee plus de 5 minutes sur
l'etape de confiance CI a cause de `Import-Certificate -CertStoreLocation
Cert:\CurrentUser\Root`, qui semble attendre une confirmation interactive
indisponible en CI headless ; corrige en remplacant par `certutil.exe
-addstore -f Root` (voir commit `f406bfc`) - un vrai bug trouve et corrige
dans le workflow de validation uniquement, aucun des trois scripts livres
(`create_test_codesigning_cert.ps1`, `sign_windows.ps1`,
`verify_windows_signature.ps1`) n'etait en cause, puisqu'aucun des trois ne
touche Trusted Root/Publishers.

- Aucun certificat public n'a ete achete ni configure.
- Aucune validation SmartScreen reelle (avec un fichier reellement marque
  "telecharge") n'a ete effectuee dans le cadre de cette phase - necessite un
  poste Windows 11 interactif, voir `docs/PACKAGING.md`.
- Aucun scan Microsoft Defender specifique a un binaire signe n'a ete refait
  dans cette phase (voir `docs/PACKAGING.md`, Phase 7.1, pour le scan Defender
  deja effectue sur le binaire non signe).
