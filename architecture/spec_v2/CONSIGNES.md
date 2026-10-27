# CONSIGNES — Atelier de spécification (Vibe Work) → Vibe Code local
> Version du 2026-10-27 (après clôture P11 et session P14). Prime sur l'ancien CONSIGNES.md de ce dossier.

## Lecture de ce dossier

Ce dossier est le canal de descente de la spécification. Lis d'abord INDEX_SPECS.md :
il liste les documents en vigueur et ceux remplacés. Tout document suffixé par une
date prime sur tout document homonyme non suffixé.

## Documents en vigueur

- FEUILLE_DE_ROUTE_V2_2026-10-27.md : feuille de route complète de la v2 (P14-P20) — source de vérité.
- CONTRAT_FORMAT_ETUDE_V2_2026-10-27.md : contrat du format étude (P14), champs chemin_absolu et buffer contractualisés.
- UI_REFORMULATION_V2.md : spécification UI de la page Reformulation (P16).
- PARAMETRAGE_LLM_V2.md : spécification du paramétrage LLM (P15).
- PROMPT_REFORMULATION_V2.md, PROMPT_RESUME_V2.md : prompts v2 (P16/P17).
- WORKFLOW_V2.md : schémas du workflow (couleur par zone).
- ARBITRAGE_P14.md : arbitrages atelier sur P14 (tous validés).
- ADDENDUM_DEMARRAGE_V2.md : historique de démarrage (P11 clos, v2 débloquée) — intégré dans la feuille de route à jour.

## Rituel de synchro (début de session + commande « synchronise avec agent de spec »)

1. Lis INDEX_SPECS.md, puis ce fichier, puis les documents nécessaires à la tâche du jour.
2. Recopie tout document nouveau ou plus récent que sa copie locale dans architecture/spec_v2/
   (remplacement ou création, jamais de fusion ni d'édition — les fichiers de l'atelier
   sont complets). Les versions avec suffixe de date remplacent leurs prédécesseurs dans
   architecture/spec_v2/ sous leur nom canonique (sans suffixe).
3. Copie architecture/PROJECT_STATE.md courant vers ce dossier (montée ; même effet que le hook post-commit).

## Règles de fond

- Ces documents sont en lecture seule pour tout agent : ne jamais les modifier.
- Monopole de publication : le CLI écrit librement dans PROJECT_STATE.md (décisions techniques,
  contraintes, écarts) mais jamais dans les documents de spec ; l'atelier ne modifie jamais
  PROJECT_STATE.md. Les arbitrages arrivent par fichiers ARBITRAGE_*.md.
- En cas de conflit apparent entre la spec et l'état réel du code : le signaler dans
  PROJECT_STATE.md et poursuivre — ne jamais improviser d'écart silencieux.
- Commits conformes à AGENTS.md : une étape de développement par commit (« Pnn - sujet : détail »).
- L'atelier ne peut pas supprimer ni remplacer les fichiers de ce dossier : les documents
  remplacés restent présents, l'INDEX indique lesquels ignorer. David peut nettoyer
  occasionnellement les fichiers marqués « REMPLACÉ ».
