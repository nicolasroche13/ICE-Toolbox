# Prochaine etape

**NEXT = valider Phase 4 (Autopilot) ET Phase 5 (Entra ID Inspector) sur un tenant Microsoft reel, apres creation et configuration de l'App Registration.**

## Etat exact au 2026-09-14

| Niveau | Phase 4 (Autopilot) | Phase 5 (Entra ID) |
| --- | --- | --- |
| Implementation (code) | Terminee | Terminee |
| Tests mockes | Terminee, tous verts (34) | Terminee, tous verts (35) |
| `compileall` | Propre | Propre |
| **Validation contre un tenant Microsoft reel** | **Non effectuee** | **Non effectuee** |

Total suite de tests : 131 (62 Phases 1 a 3.1 + 34 Autopilot + 35 Entra ID), tous verts, aucune regression.

Ne pas ecrire "Autopilot valide" ni "Entra ID valide" ni "Phase 4/5 tenant-validated" nulle part tant que les deux lignes ci-dessus ne sont pas passees a "Terminee". Voir `docs/GRAPH_PERMISSIONS.md` (section "Validation tenant reel") et `docs/ROADMAP.md` (Phases 4 et 5) pour le detail.

## Pourquoi ce n'est pas encore fait

Aucune App Registration Microsoft Entra ID n'existe encore pour Endpoint Toolbox. Aucun `~/.endpoint_toolbox/graph_config.json`, aucun secret dans le Keychain/Credential Manager sur les machines de developpement utilisees jusqu'ici. La Phase 5 a ete implementee sans attendre cette validation (demande explicite : ne pas bloquer le developpement pour cette raison), mais reste elle aussi non confrontee a un tenant reel.

## Action que l'utilisateur doit faire lui-meme

1. Creer l'App Registration dans Microsoft Entra ID (checklist precise : voir `docs/GRAPH_PERMISSIONS.md` et `docs/DEVELOPMENT.md`).
2. Ajouter les 3 permissions Application deja documentees et accorder l'Admin Consent :
   - `DeviceManagementManagedDevices.Read.All`
   - `Device.Read.All`
   - `DeviceManagementServiceConfig.Read.All`
3. Configurer Endpoint Toolbox (Settings > Tenant ID / Client ID / Client Secret > Test Connection > Save Configuration). Note : Test Connection n'exerce que `DeviceManagementManagedDevices.Read.All` ; les permissions Entra ID et Autopilot ne se verifient qu'en utilisant reellement ces pages.
4. Revenir avec l'agent (Claude/Codex) pour reprendre la checklist de validation terrain :
   - **Autopilot** : recherche multi-identifiant, `contains(serialNumber, ...)`, profil beta, correlation Intune/Entra, les 10 Health rules, `identifier_mismatch` (risque de faux positif documente a verifier en priorite), erreurs partielles, Support Bundle, UI reelle.
   - **Entra ID** : recherche par Object ID / deviceId / displayName (egalite exacte) / serial / Managed Device ID, correlation Intune/Autopilot, les 5 Health rules, definition du seuil "stale" a 90 jours, erreurs partielles (401/403/404/429/5xx), Support Bundle, UI reelle.

## Rappels stricts pendant cette validation

- Strictement READ-ONLY : aucun POST/PATCH/PUT/DELETE Graph, aucune action Intune/Entra ID/Autopilot.
- Ne pas ajouter de permission Graph supplementaire sans la documenter et la valider avant implementation.
- Ne pas modifier `identifier_mismatch`, `os_version_mismatch` (deliberement non implementee, voir D026) ou toute autre regle Health avant d'avoir demontre un probleme reel avec des valeurs concretes.
- Ne jamais committer de tenant ID reel inutile, client ID reel, client secret, token, Authorization header, serial number reel ou device ID reel. Utiliser des valeurs sanitisees dans toute documentation.
- Ne pas commencer la Phase 6 (Entra ID au-dela de l'inspection device : users, groups, Conditional Access) avant que les Phases 4 et 5 soient validees en conditions reelles.
