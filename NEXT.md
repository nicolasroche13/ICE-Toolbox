# Prochaine etape

**NEXT = valider la Phase 4 Autopilot Troubleshooter sur un tenant Microsoft reel, apres creation et configuration de l'App Registration.**

## Etat exact au 2026-09-14

| Niveau | Statut |
| --- | --- |
| Implementation Phase 4 (code) | Terminee |
| Tests mockes (96, dont 34 Autopilot) | Terminee, tous verts |
| `compileall` | Propre |
| **Validation contre un tenant Microsoft reel** | **Non effectuee** |

Ne pas ecrire "Autopilot valide" ou "Phase 4 tenant-validated" nulle part tant que la ligne ci-dessus n'est pas passee a "Terminee". Voir `docs/GRAPH_PERMISSIONS.md` (section "Validation tenant reel") et `docs/ROADMAP.md` (Phase 4) pour le detail.

## Pourquoi ce n'est pas encore fait

Aucune App Registration Microsoft Entra ID n'existe encore pour Endpoint Toolbox. Aucun `~/.endpoint_toolbox/graph_config.json`, aucun secret dans le Keychain/Credential Manager sur les machines de developpement utilisees jusqu'ici.

## Action que l'utilisateur doit faire lui-meme

1. Creer l'App Registration dans Microsoft Entra ID (checklist precise : voir le rapport de session ou `docs/GRAPH_PERMISSIONS.md`).
2. Ajouter les 3 permissions Application deja documentees (`DeviceManagementManagedDevices.Read.All`, `Device.Read.All`, `DeviceManagementServiceConfig.Read.All`) et accorder l'Admin Consent.
3. Configurer Endpoint Toolbox (Settings > Tenant ID / Client ID / Client Secret > Test Connection > Save Configuration).
4. Revenir avec l'agent (Claude/Codex) pour reprendre la checklist de validation terrain (recherche multi-identifiant, `contains(serialNumber, ...)`, profil beta, correlation Intune/Entra, les 10 Health rules, `identifier_mismatch`, erreurs partielles, Support Bundle, UI reelle).

## Rappels stricts pendant cette validation

- Strictement READ-ONLY : aucun POST/PATCH/PUT/DELETE Graph, aucune action Intune/Entra/Autopilot.
- Ne pas ajouter de permission Graph supplementaire sans la documenter et la valider avant implementation.
- Ne pas modifier `identifier_mismatch` (ou toute autre regle Health) avant d'avoir demontre un faux positif reel avec des valeurs concretes.
- Ne jamais committer de tenant ID reel inutile, client ID reel, client secret, token, Authorization header, serial number reel ou device ID reel. Utiliser des valeurs sanitisees dans toute documentation.
- Ne pas commencer la Phase 5 (Entra ID read-only) avant que la Phase 4 soit validee en conditions reelles.
