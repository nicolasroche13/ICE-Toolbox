# Development

## Demarrage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Sous Windows :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Regles de contribution

- Garder la logique metier hors de `app/ui`.
- Ne pas ajouter de client Graph tant que la phase read-only n'est pas cadree.
- Ne jamais stocker de secret, tenant ID ou chemin machine en dur.
- Ne pas ajouter de base de donnees ni de serveur web local.
- Preferer des fonctions pures pandas pour les traitements testables.
- Ajouter ou ajuster les tests quand le comportement du Ring Builder change.

## Modules importants

- `app/deployment/ring_builder.py` : moteur de repartition, exclusions, syntheses et pilote representatif.
- `app/io/tables.py` : lecture CSV/XLSX/XLSM.
- `app/io/exporters.py` : export CSV/XLSX non destructif.
- `app/models/deployment.py` : dataclasses partagees.
- `app/ui/main_window.py` : UI PySide6 et orchestration worker/thread.

## UI

`DeploymentToolsPage` gere :

- import par bouton ou drag-and-drop ;
- selection des criteres de stratification ;
- configuration des modes ;
- exclusions ;
- preview ;
- export.

Les traitements potentiellement longs passent par `TaskWorker` + `QThread`.

## Donnees de test manuel

Un fichier minimal doit contenir au moins une colonne d'identification, par exemple `DeviceName`. Les colonnes comme `Site`, `Model`, `OSVersion` et `Manufacturer` activent une preview plus utile pour la stratification.
