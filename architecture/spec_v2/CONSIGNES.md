# CONSIGNES — Atelier de spécification (Vibe Work) → Vibe Code local

> Ce fichier est écrit et tenu à jour par l'atelier de spécification (Vibe Work).
> Il arrive dans ce dossier par synchronisation Drive : aucune action manuelle nécessaire.
> Dernière mise à jour : 2026-10-27.

## Rôle de ce dossier

- FEUILLE_DE_ROUTE_V2.md : feuille de route complète de la v2 (phases P14 à P20) — la source de vérité de la spécification.
- PROMPT_REFORMULATION_V2.md : prompt de reformulation biblique v2 — valeur par défaut du bloc Reformulation (P16).
- PROMPT_RESUME_V2.md : prompt de résumé d'étude biblique v2 — valeur par défaut du bloc Résumé (P17).
- WORKFLOW_V2.md : schémas du workflow (vue d'ensemble + vue détaillée, format Mermaid).
- PROJECT_STATE.md (copié par le hook post-commit) : ton état du code, remonté à l'atelier.

## Règles pour chaque session

1. En DÉBUT de session : lire ce fichier et FEUILLE_DE_ROUTE_V2.md (sections 0 et phases concernées).
2. La v2 (P14 et suivants) ne démarre qu'après la livraison de P11 (packaging Windows v1.0).
3. En cas de conflit apparent entre ces documents et l'état réel du code : le signaler dans PROJECT_STATE.md et l'atelier tranchera — ne pas improviser d'écart silencieux.
4. Les décisions d'architecture prises à l'atelier (principes directeurs, section 2 de la feuille de route) ne se contournent pas au niveau du code sans en reparler.
5. Conserver les conventions v1 : commits d'une étape de développement à la fois (Pnn - sujet : détail), tests écrits au fil des phases, i18n français de l'UI.

## Points d'attention v2 (rappels des principes)

- Non-destructif : un traitement ne modifie jamais le texte source.
- Format étude : dossier contenant et référençant des projets v1 inchangés ; FID stable par bloc de parole ; résultats stockés par bloc avec historique complet des versions.
- Journal des opérations de prétraitement à persister dès P14 (silences supprimés : positions, durées originales, accélération) — conversions position traité ↔ original testées unitairement.
- Prompts v2 éditables dans les paramètres de l'étude, intégrés comme valeurs par défaut.
- Contrôles qualité locaux (gratuits) : rapport de longueur, références ajoutées/perdues, interdits stylistiques, emphase ; le LLM ne sert qu'au langage.
