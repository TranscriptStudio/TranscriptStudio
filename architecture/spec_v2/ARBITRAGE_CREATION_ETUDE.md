# ARBITRAGE_CREATION_ETUDE — assouplissement de la règle « dossier vide » (P14.3)

Date : 2026-10-27 · Publié par l'atelier · Concerne `creer_etude` (services/etude_io.py) + dialogue « Nouvelle étude » (P14.3).

## Constat

David a tenté de créer une étude dans un sous-dossier existant non vide (« Évangile de Luc », qui regroupe ses projets v1) ; `creer_etude` refuse tout dossier non vide. Le réflexe est légitime et même souhaitable : placer l'étude à côté des projets référencés rend les chemins relatifs robustes. La règle « vide ou inexistant » est trop rigide ; sa seule valeur est d'éviter un écrasement silencieux.

## Arbitrage (décision atelier, validée par David le 2026-10-27)

1. **Dossier non vide autorisé** pour la création d'une étude, **avec confirmation explicite** dans l'UI : « Ce dossier contient déjà des fichiers. Créer l'étude ici quand même ? » (énumérer le nombre d'éléments présents).
2. **Refus dur uniquement** si le dossier contient déjà un `etude.json` (ce serait une autre étude — message : « Ce dossier est déjà une étude ; l'ouvrir plutôt ? », et proposer son ouverture).
3. Aucun fichier existant n'est jamais modifié ni supprimé : la création n'écrit que `etude.json` et les sous-dossiers de l'étude (`reunions/`, `blocs/`, `traitements/`, `synthese/`, `parametres/`). En cas de conflit de nom avec un élément existant non-étude (ex. un fichier `blocs`), erreur claire sans rien écrire.
4. Le message d'erreur actuel est complété d'une aide : « Saisissez plutôt un nom de nouveau dossier pour créer l'étude dedans. »

## Impact contrat

Le contrat du format étude (§2) reste inchangé : il décrit la structure du dossier étude, pas la vacuité préalable du répertoire hôte. Aucune règle d'invariance touchée (toujours non-destructif).

## Livraison

Correctif à intégrer à la prochaine session CLI (tests unitaires : création dans dossier non vide OK avec confirmation, refus si etude.json présent, rien d'écrasé) — pas une phase nouvelle.