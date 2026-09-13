# Endpoint Toolbox

Endpoint Toolbox est une application desktop Python/PySide6 pour les ingenieurs Endpoint et Microsoft 365.

La Phase 1 livre un socle local robuste centre sur les Deployment Tools. Aucun appel Microsoft Graph, Intune, Entra ID ou Autopilot n'est encore implemente.

## Perimetre Phase 1

- Application desktop PySide6, sans serveur web local.
- Navigation principale : Home, Intune, Entra ID, Autopilot, Deployment Tools, Settings.
- Intune, Entra ID et Autopilot restent des placeholders.
- Deployment Tools fonctionnel pour CSV, XLSX et XLSM en lecture.
- Ring Builder independant de PySide6 et teste avec pytest.
- Aucune ecriture Microsoft, aucun secret et aucune execution PowerShell.

## Deployment Tools

Le workflow cible est disponible :

1. Ouvrir l'application avec `python main.py`.
2. Aller dans Deployment Tools.
3. Glisser ou selectionner un fichier `csv`, `xlsx` ou `xlsm`.
4. Verifier le nombre de lignes, les colonnes et la preview.
5. Choisir Simple Split, Progressive Rings, Custom Sizes ou Representative Pilot.
6. Configurer exclusions, seed et criteres de stratification.
7. Generer la preview.
8. Exporter en CSV ou XLSX, globalement et/ou par ring.

## Installation

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Tests

```bash
pytest -q
```

Si `pytest` n'est pas dans le PATH :

```bash
python -m pytest -q
```

## Documentation

- `docs/ARCHITECTURE.md` : structure applicative et responsabilites.
- `docs/FEATURES.md` : fonctionnalites livrees et backlog.
- `docs/DECISIONS.md` : decisions produit et techniques.
- `docs/ROADMAP.md` : prochaines phases.
- `docs/DEVELOPMENT.md` : guide de reprise pour agents/developpeurs.
- `docs/TESTING.md` : strategie de tests.
