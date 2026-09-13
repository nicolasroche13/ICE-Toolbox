# Testing

## Commande principale

```bash
pytest -q
```

Avec le virtualenv local :

```bash
./.venv/bin/python -m pytest -q
```

## Compilation Python

Sur macOS sandboxe, utiliser un cache temporaire autorise :

```bash
PYTHONPYCACHEPREFIX=/private/tmp/endpointtoolbox-pycache ./.venv/bin/python -m compileall main.py app tests
```

## Couverture actuelle

Les tests couvrent :

- split egal ;
- population non divisible ;
- progressive rings ;
- arrondis ;
- custom sizes ;
- ring Remaining ;
- exclusions ;
- doublons ;
- stratification ;
- representative pilot ;
- stabilite avec seed ;
- aucune ligne perdue ;
- aucune ligne affectee deux fois ;
- imports CSV/XLSX ;
- exports CSV/XLSX ;
- prevention d'ecrasement silencieux.

## Gaps connus

- Pas encore de tests UI automatises.
- Pas encore de benchmark sur tres gros fichiers.
- Pas encore de test Windows CI.

Ces gaps sont acceptes pour Phase 1 mais prioritaires avant packaging entreprise.
