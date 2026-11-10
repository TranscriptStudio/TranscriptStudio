# INDEX_SPECS — documents de spécification TranscriptStudio v2

Mis à jour : 2026-11-10a (atelier, rév. 4). **Session du soir du 09/11 : reliquat v2 LIVRÉ en une session — 9 commits (4f049c1 → e00ceeb) : P18.9 correctifs page Étude, P18.10 lecteur de Bible intégré, P20.1 mobilité inter-blocs, P20.2 sous-titres IA, P20.3 aides à la relecture (page Ouvrage seule), P20.4 export DOCX structuré, P20.5 référence de contrôle qualité par portée (§8bis : aucune écriture en retour), P20.6 synthèse d'étude repensée, P20 fin retrait de la compatibilité FID nu + README/manuel DOCX. 788 tests verts ; origin/master inchangé à l'état v1 (P13).** **Le développement v2 est intégralement livré : reste la recette humaine du reliquat par David (P18.9, P18.10, P20.1 → P20.6, retrait FID nu), puis clôture v2.** Écarts CLI : manuel PDF à régénérer par l'atelier (DOCX à jour, pas de convertisseur DOCX→PDF côté dev) ; vérification par tests ciblés d'étape en worktree + suite complète (788) en arbre principal avant commit final (worktrees instables : XML Bible non versionnés) ; hunk mixte sans impact (réglage export_ouvrage commité avec P18.10, utilisé par P20.4). **Recette en cours (David, 10/11) : P18.9 reçue — relecture 2 consignée en P18.9-bis (SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_2026-11-10b, §7, invariants 15-19 : numérotation positionnelle en gouttière à gauche (labels fixes, aucun sans tuile), « Renommer… » au clic droit, info-bulles supprimées, plus aucune mention Bible sur la page Étude, boutons haut droit) et non-conformité P20.6b relevée (« Alimenter la synthèse globale » absent du menu contextuel des tuiles — invariant 9) ; correctifs à livrer par le CLI avant la suite de la recette.** **Relecture 3 (dialogue « Paramètres de l'étude », 10/11) : P18.11 consigné (SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_2026-11-10b, §8, invariants 20-22) — dialogue allégé : plus aucun paramètre LLM ni prompt, seuls les champs d'étude restent (titre/thème, options de contexte + champ tokens, longueur cible, source par défaut, Bible + propagation, interdits stylistiques) ; ABROGATION de la surcharge d'étude (synthèse = réglages de l'app : paramètres LLM globaux + prompt de la bibliothèque prompts/synthese_etude.md ; volets LLM existants inertes, jamais réécrits, aucune migration) ; CONTRAT_STOCKAGE_REUNIONS_V2 §8/§9 mis à jour en conséquence ; à livrer par le CLI avec la série 2.** **Maquette illustrative de la page Étude publiée : MAQUETTE_PAGE_ETUDE_P18_9_BIS_2026-11-10c.html — elle illustre les changements discutés (relectures 1-2), ce n'est PAS une référence stricte d'UI : l'UI n'a pas à être refaite selon elle (réserve David du 10/11).** **Plus aucun arbitrage en attente.** **Règle : un document suffixé par une date prime sur son homonyme non suffixé ; en cas de plusieurs suffixes le même jour, la lettre la plus loin dans l'alphabet prime ; les suffixes les plus récents priment.** Le CLI recopie tout fichier nouveau ou plus récent dans architecture/spec_v2/. Source de vérité de la descente : skill partagé transcriptstudio-spec (v53).

| Document | Fichier courant | Phase |
|---|---|---|
| Feuille de route | **FEUILLE_DE_ROUTE_V2_2026-11-10a.md** | toutes |
| Contrat du format étude | CONTRAT_FORMAT_ETUDE_V2_2026-10-29.md | P14 |
| Contrat stockage réunion (P18.7 + P18.11) | CONTRAT_STOCKAGE_REUNIONS_V2_2026-11-09a.md | P18.7 — LIVRÉ, prime sur le contrat format étude ; §8/§9 amendés le 10/11 (abrogation de la surcharge d'étude) |
| Spécification moteur | SPEC_MOTEUR_P15_V2_2026-10-27.md | P15.3/P15.4 |
| Spec UI Reformulation | UI_REFORMULATION_V2_2026-10-27b.md | P16 |
| Correctifs UI Reformulation (séries 1-4) | UI_REFORMULATION_MODIFS_V2_2026-10-30f.md | P16-bis |
| Paramétrage LLM | PARAMETRAGE_LLM_V2_2026-10-31c.md | P15 |
| Gestion des prompts (bibliothèque + éditeur) | UI_GESTION_PROMPTS_V2_2026-10-31a.md | P16-ter |
| Addendum Bibles + lecteur de Bible | BIBLE_JND_V2_2026-11-09d.md | P18.5 + P18.9c + P18.10 (lecteur intégré) — LIVRÉ |
| Spec navigation (hub, Réunion, Étude, Ouvrage) | SPEC_NAVIGATION_V2_2026-10-29b.md | P18.6 |
| Correctifs de relecture navigation (séries 1-8) | SPEC_NAVIGATION_MODIFS_V2_2026-10-31e.md | P18.6-bis |
| Correctifs page Étude & synthèse repensée (séries 1-3) | **SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_2026-11-10b.md** | P18.9 + P20.6 livrés (4f049c1, 895f3e0) + P18.9-bis + P18.11 à livrer + conformité P20.6b |
| Prompt reformulation v2 | PROMPT_REFORMULATION_V2.md | P16 |
| Prompt résumé v2 | PROMPT_RESUME_V2.md | P17 |
| Workflow (schémas) | WORKFLOW_V2_2026-10-27.md | — |
| Arbitrage P14 | ARBITRAGE_P14.md | clos |
| Arbitrage P15 | ARBITRAGE_P15.md | clos |
| Arbitrage création d'étude | ARBITRAGE_CREATION_ETUDE.md | correctif P14.3 |
| Arbitrage exclusivité réunions/études | ARBITRAGE_EXCLUSIVITE_REUNIONS_2026-10-29.md | P18.6 |
| Arbitrage P19.4 fusions/régénération | ARBITRAGE_P19_4_FUSION_REGENERATION_2026-11-07a.md | P19.4 — VALIDÉ |
| Arbitrage prompt de fusion (bibliothèque éditable) | ARBITRAGE_PROMPT_FUSION_2026-11-07a.md | P19.4-bis — VALIDÉ |
| Correctifs relance ciblée sur sélection | CORRECTIFS_RELANCE_CIBLEE_V2_2026-11-07b.md | P16-bis/P17 — correctif |
| Arbitrage écarts P18.7 | ARBITRAGE_P18_7_ECARTS_2026-11-09a.md | P18.7 — conformité ACTÉE (écart 5 : retrait FID nu LIVRÉ en P20 fin) |

Rappel (David, 2026-10-28) : version Bible **par défaut = darbyR (Darby révisée)** — la versification n'est plus affichée séparément (P18.9c).
