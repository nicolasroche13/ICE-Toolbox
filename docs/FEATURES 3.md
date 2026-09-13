# Fonctionnalites

## Phase 1 livree

- [x] Shell PySide6 redimensionnable.
- [x] Navigation principale : Home, Intune, Entra ID, Autopilot, Deployment Tools, Settings.
- [x] Placeholders explicites pour Intune, Entra ID et Autopilot.
- [x] Import CSV avec detection de separateur et fallback d'encodages courants.
- [x] Import XLSX et XLSM en lecture.
- [x] Apercu limite pour eviter de saturer l'UI.
- [x] Simple Split en N rings equilibres.
- [x] Melange deterministe avec seed configurable.
- [x] Progressive Rings avec noms, pourcentages, somme 100% obligatoire et arrondis controles.
- [x] Custom Sizes avec tailles exactes et ring Remaining.
- [x] Exclusions collees ou chargees depuis un fichier texte.
- [x] Choix de la colonne d'identification.
- [x] Rapport d'exclusions : demandes, exclus, non trouves, doublons.
- [x] Stratification sur une ou plusieurs colonnes.
- [x] Representative Pilot avec taille cible, criteres et score de representativite.
- [x] Preview des rings : nom, lignes, pourcentage, criteres distincts.
- [x] Preview des donnees assignees avec colonne `Ring`.
- [x] Export global CSV/XLSX.
- [x] Export CSV/XLSX par ring.
- [x] Protection contre l'ecrasement silencieux des exports.
- [x] Workers Qt pour chargement et generation de preview.
- [x] Tests pytest du moteur et de l'IO.

## Hors perimetre Phase 1

- [ ] Microsoft Graph.
- [ ] Authentification Entra.
- [ ] APIs Intune, Entra ID et Autopilot.
- [ ] Application Deployment Monitoring.
- [ ] Packaging Windows.
- [ ] Signature de l'application.

## Backlog local court terme

- [ ] Ameliorer l'affichage detaille des distributions global vs ring.
- [ ] Ajouter un export dedie du rapport d'exclusions.
- [ ] Ajouter une vraie progression numerique pour les tres gros fichiers.
- [ ] Ajouter tests UI smoke avec Qt en mode headless si l'environnement CI le permet.
