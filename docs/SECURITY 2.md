# Sécurité

## Principes
- Aucune écriture dans Entra ID ou Intune.
- Traitement CSV/XLSX local.
- Pas de serveur web local.
- Pas d'exécution PowerShell arbitraire.
- Pas de téléchargement/exécution dynamique de code.
- Dépendances Python figées avant packaging de production.
- Package Windows à signer avant diffusion en entreprise.
- Build Windows réalisé/testé sur Windows ou CI Windows.

## Données
Par défaut, aucun fichier utilisateur n'est conservé par l'application après fermeture hors exports explicitement demandés.
