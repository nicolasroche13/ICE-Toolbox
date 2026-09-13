# Architecture

## Objectif

Endpoint Toolbox est une application desktop locale pour preparer et analyser des donnees Endpoint / Microsoft 365.

- Plateforme cible principale : Windows 11.
- Developpement possible sur macOS.
- UI : PySide6.
- Traitement local : pandas / openpyxl.
- Tests : pytest.
- Microsoft Graph : reserve a une phase ulterieure, strictement read-only.
- Aucun serveur local, aucune base de donnees, aucune execution PowerShell arbitraire.

## Structure

- `main.py` : point d'entree minimal.
- `app/ui` : fenetres et widgets PySide6.
- `app/deployment` : logique metier Deployment Tools et Ring Builder.
- `app/models` : dataclasses partagees entre UI, moteur et export.
- `app/io` : import CSV/XLSX/XLSM et exports CSV/XLSX.
- `app/config` : constantes applicatives.
- `app/utils` : utilitaires transverses.
- `app/intune`, `app/entra`, `app/autopilot`, `app/graph` : espaces reserves pour futures phases.
- `tests` : tests pytest du moteur et de l'IO.

## Separation des responsabilites

La logique du Ring Builder ne depend pas de PySide6. L'UI collecte les options, lance les traitements dans un worker Qt et affiche les resultats, mais les fonctions de repartition restent testables sans interface graphique.

Le flux principal est :

1. `app.io.tables.load_table` lit un fichier utilisateur.
2. `app.deployment.ring_builder` applique exclusions, repartition et syntheses.
3. `app.io.exporters.export_rings` ecrit les fichiers de sortie sans ecraser silencieusement.
4. `app.ui.main_window.DeploymentToolsPage` orchestre le workflow desktop.

## Ring Builder

Modes supportes :

- Simple Split : repartition equitable en N rings.
- Progressive Rings : tailles calculees par pourcentages dont la somme doit etre 100%.
- Custom Sizes : tailles exactes avec option Remaining.
- Representative Pilot : pilote stratifie avec ring Remaining.

Les algorithmes sont deterministes avec seed. La stratification cree un ordre de lignes dont chaque prefixe approche la distribution globale des criteres selectionnes, puis les tailles de rings sont appliquees sur cet ordre.

## Representative Pilot

Le score de representativite est volontairement simple :

`100 - moyenne des ecarts absolus maximum par critere, exprimes en points de pourcentage`

Ce n'est pas un score statistique scientifique. Il sert d'indicateur operationnel lisible pour comparer rapidement la distribution globale et la distribution du pilote.

## UI et threading

Les traitements de chargement et de generation de preview passent par `TaskWorker` et `QThread` afin d'eviter de bloquer l'interface. La barre de progression est indeterminee pour cette phase.

## Contraintes de securite

- Pas de secret dans le code source.
- Pas de tenant ID code en dur.
- Pas d'ecriture Intune / Entra / Graph.
- Pas de serveur web local.
- Pas d'ecrasement silencieux lors des exports.
