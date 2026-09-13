# Roadmap

## Phase 1 - Socle local et Deployment Tools

Statut : implemente.

- Shell desktop PySide6.
- Navigation principale.
- Import CSV/XLSX/XLSM.
- Simple Split.
- Progressive Rings.
- Custom Sizes.
- Exclusions.
- Stratification.
- Representative Pilot.
- Preview.
- Export CSV/XLSX global et par ring.
- Tests pytest du moteur.

## Phase 1.1 - Durcissement local

- Export du rapport d'exclusions.
- Tableau detaille global vs ring pour les distributions.
- Progression numerique pour gros traitements.
- Smoke tests UI si environnement CI compatible Qt.
- Validation Windows 11.
- Packaging initial Windows.

## Phase 2 - Configuration read-only Microsoft

- Page Settings pour configuration locale.
- Choix d'un mode d'authentification read-only.
- Documentation des permissions Graph minimales.
- Client Graph read-only sans operation d'ecriture.
- Gestion des erreurs d'autorisation.

## Phase 3 - Intune read-only

- Device Inspector.
- Device Health.
- Policy Inspector.
- Assignment Explorer.
- Application Deployment Monitoring en lecture uniquement.

## Phase 4 - Autopilot read-only

- Autopilot Inspector.
- Fleet Health.
- Analyse de deploiement.

## Phase 5 - Entra ID read-only

- User Inspector.
- Group Inspector.
- Group Compare.
- Enterprise Apps / Service Principals.
- Conditional Access Inspector.
