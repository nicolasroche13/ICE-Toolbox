# Endpoint Toolbox

Application desktop Python/PySide6 destinée aux ingénieurs Endpoint / Microsoft 365.

## Périmètre V1
- Lecture uniquement côté Microsoft Graph
- Intune
- Entra ID
- Autopilot
- Suivi de déploiement d'applications
- Deployment / Ring Builder
- Aucun changement écrit dans le tenant

## Démarrage sur macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Démarrage sur Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Première fonctionnalité disponible
Le module **Deployment Tools > Ring Builder** permet :
- d'importer un CSV ou XLSX ;
- de choisir le nombre de lots ;
- de répartir les lignes de façon équilibrée ;
- d'exporter un fichier XLSX global avec une colonne `Ring` ;
- d'exporter un XLSX séparé par lot.

Voir `docs/ROADMAP.md` pour la suite.
