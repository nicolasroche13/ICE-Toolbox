# Permissions Microsoft Graph

Aucune permission Graph n'est nécessaire pour le premier Ring Builder.

Les permissions de la V1 seront documentées module par module et devront respecter le principe du moindre privilège.

Contraintes :
- Application permissions uniquement pour le mode app-only prévu.
- Lecture seule.
- Aucune permission `*.ReadWrite.All` dans la V1.
- Secret ou certificat stocké hors du code source.
