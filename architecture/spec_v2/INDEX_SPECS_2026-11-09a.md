# INDEX_SPECS — documents de spécification TranscriptStudio v2

Mis à jour : 2026-11-09a (atelier). Nouveau : **CONTRAT_STOCKAGE_REUNIONS_V2_2026-11-09a.md (P18.7)** — stockage des traitements au niveau réunion : tier `transcriptstudio\` additif dans le projet v1, FID à portée réunion (identité = couple (réunion, FID)), étude v2 (`etude_format_version: 2`) ne gardant que ordre/gabarit/titre_1, synthèse, surcharges (synthèse seule), journal étude ; aucune écriture en retour étude/ouvrage → réunion (§8bis) ; migration one-shot v1→v2 à l'ouverture (sauvegarde, éclatement du registre, requalification des provenances ouvrage, contrôle d'intégrité avant suppression, idempotente, reprenable). **Prime sur CONTRAT_FORMAT_ETUDE_V2 pour les points traités** (registre global d'étude du 2026-10-27 abrogé). Nouveau : **ARBITRAGE_P18_7_ECARTS_2026-11-09a.md** — conformité de la livraison P18.7 (08/11, 697 tests verts) ACTÉE ; propagation des paramètres d'étude vers les tiers VALIDÉE si explicite ; badge Bible « commune + Bibles mixtes » ; invariant 1 reformulé ACCEPTÉ ; compatibilité FID nu transitoire, retrait exigé en P20. Nouveau : **FEUILLE_DE_ROUTE_V2_2026-11-09a.md** — état au 09/11 : P19 livré dans son intégralité (07/11), P18.7 LIVRÉ (08/11), P18.8 ajoutée (titre de réunion éditable, bouton « Paramètres de l'étude », sélecteur de version de la Bible avec propagation aux tiers) ; restent P18.8, recette humaine, P20. **Règle : un document suffixé par une date prime sur son homonyme non suffixé ; en cas de plusieurs suffixes le même jour, la lettre la plus loin dans l'alphabet prime ; les suffixes les plus récents priment.** Le CLI recopie tout fichier nouveau ou plus récent dans architecture/spec_v2/. Source de vérité de la descente : skill partagé transcriptstudio-spec (v40).

| Document | Fichier courant | Phase |
|---|---|---|
| Feuille de route | **FEUILLE_DE_ROUTE_V2_2026-11-09a.md** | toutes |
| Contrat du format étude | CONTRAT_FORMAT_ETUDE_V2_2026-10-29.md | P14 |
| **Contrat stockage réunion (P18.7)** | **CONTRAT_STOCKAGE_REUNIONS_V2_2026-11-09a.md** | **P18.7 — LIVRÉ, prime sur le contrat format étude** |
| Spécification moteur | SPEC_MOTEUR_P15_V2_2026-10-27.md | P15.3/P15.4 |
| Spec UI Reformulation | UI_REFORMULATION_V2_2026-10-27b.md | P16 |
| Correctifs UI Reformulation (séries 1-4) | UI_REFORMULATION_MODIFS_V2_2026-10-30f.md | P16-bis |
| Paramétrage LLM | PARAMETRAGE_LLM_V2_2026-10-31c.md | P15 |
| Gestion des prompts (bibliothèque + éditeur) | UI_GESTION_PROMPTS_V2_2026-10-31a.md | P16-ter |
| Addendum Bibles | BIBLE_JND_V2_2026-10-28b.md | P18.5 |
| Spec navigation (hub, Réunion, Étude, Ouvrage) | SPEC_NAVIGATION_V2_2026-10-29b.md | P18.6 |
| Correctifs de relecture navigation (séries 1-8) | SPEC_NAVIGATION_MODIFS_V2_2026-10-31e.md | P18.6-bis |
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
| **Arbitrage écarts P18.7** | **ARBITRAGE_P18_7_ECARTS_2026-11-09a.md** | **P18.7 — conformité ACTÉE** |

Rappel (David, 2026-10-28) : version Bible **par défaut = darbyR (Darby révisée)**. **Reste à faire : P18.8** (correctifs de relecture du 08/11, commandes prêtes), **recette humaine P16/P17/P18/P18.6/P18.7/P19 par David** (checklist fin de session P17 du PROJECT_STATE, à compléter du parcours P18.7 : migration de l'étude de recette + réunion autonome avec reformulation/résumé hors étude), puis **P20** : détection des pensées similaires, sous-titres IA, aides à la relecture, export DOCX structuré, retrait de la compatibilité FID nu.
