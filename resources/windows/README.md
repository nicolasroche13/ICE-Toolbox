# Icone Windows

Aucune icone Endpoint Toolbox n'existe actuellement dans ce depot - aucune identite
visuelle n'a ete inventee pour cette phase de packaging.

Pour ajouter une icone reelle plus tard :

1. Placer un fichier `app.ico` dans ce dossier (`resources/windows/app.ico`).
2. Ne rien changer d'autre : `packaging/windows/EndpointToolbox.spec` detecte
   automatiquement ce fichier a la compilation (`Path.exists()`) et l'attache a
   `EndpointToolbox.exe` s'il est present, sans le rendre obligatoire.

Sans ce fichier, PyInstaller compile l'executable avec l'icone par defaut de
PyInstaller/Windows - ce n'est pas un bug, c'est le comportement attendu tant
qu'aucune icone reelle n'est fournie.
