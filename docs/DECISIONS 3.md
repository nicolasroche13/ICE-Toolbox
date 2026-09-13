# Decisions

## D001 - Application desktop Python

Decision : Python + PySide6.

Raison : cible Windows desktop, developpement possible sur macOS, integration simple avec pandas/openpyxl.

## D002 - Microsoft read-only

Decision : aucune action d'ecriture Intune, Entra ou Graph dans la V1.

La Phase 1 ne contient aucun client Graph. Les modules `app/intune`, `app/entra`, `app/autopilot` et `app/graph` restent vides ou placeholders.

## D003 - Traitements locaux

Decision : les CSV/XLSX sont traites localement en memoire avec pandas.

Pas de base de donnees, pas de service local, pas d'upload.

## D004 - Moteur independant de l'UI

Decision : `app.deployment.ring_builder` ne depend pas de PySide6.

Raison : le Ring Builder doit etre testable, reutilisable et fiable sans lancer l'application graphique.

## D005 - Stratification deterministe

Decision : la stratification utilise un ordre deterministe avec seed. Chaque prefixe de l'ordre cherche a approcher la distribution globale des strates selectionnees, puis les tailles de rings sont appliquees.

Raison : cela fonctionne pour Simple Split, Progressive Rings, Custom Sizes et Representative Pilot avec une seule approche.

## D006 - Score Representative Pilot simple

Decision : score = `100 - moyenne des ecarts absolus maximum par critere`.

Raison : score comprehensible par un ingenieur, utile pour comparer rapidement, sans pretendre a une validite statistique avancee.

## D007 - Exports non destructifs

Decision : un export ne remplace jamais silencieusement un fichier existant. Un suffixe numerique est ajoute si besoin.

## D008 - Pas de dependances lourdes

Decision : Phase 1 reste limitee a PySide6, pandas, openpyxl et pytest.

Raison : limiter la surface de maintenance et de packaging.
