# INDEX_SPECS — documents de spécification TranscriptStudio v2

Mis à jour : 2026-11-07c (atelier). Nouveau : **ARBITRAGE_PROMPT_FUSION_2026-11-07a.md (P19.4-bis)** — le prompt de fusion assistée passe dans la bibliothèque éditable prompts/fusion.md (règles P16-ter : mode source, ⚙ Prompts, copie locale par étude, traçabilité texte+hash) ; règle générale : aucun prompt LLM codé en dur. Nouveau : **ARBITRAGE_P19_4_FUSION_REGENERATION_2026-11-07a.md** — validation officielle de l'interprétation P19.4 soumise par le CLI : une fusion de pensées est une édition du document dérivé, jamais défaite automatiquement (inv. A) ; seule la régénération explicite (P19.3, avec avertissement mentionnant les fusions) peut l'écraser (inv. B) ; traçabilité et dé-fusion conservées (inv. C). Détection des pensées similaires confirmée en P20.  État constaté au PROJECT_STATE du 07/11 : **P19 LIVRÉ DANS SON INTÉGRALITÉ** (P19.1 modèle de données, P19.2 page Ouvrage trois zones, P19.3 génération/régénération, P19.4 fusion de pensées), 613 tests verts ; P18.6-bis séries 1-8, P16-ter, P20/P20-bis/P20-ter livrés.  Ajouts précédents : UI_GESTION_PROMPTS_V2 (31a) ; série 8 navigation (31e, fusion de l'outillage dans la page Résumé) ; série 7 (balayage lumineux unique, pastilles cliquables page Réunion) ; échelles d'effort par modèle ; Le Chonk au catalogue ; série 6 (pastilles uniformisées) ; 4ᵉ série UI Reformulation (progression par blocs) ; séries 1-5 correctifs navigation. **Règle : un document suffixé par une date prime sur son homonyme non suffixé ; en cas de plusieurs suffixes le même jour, la lettre la plus loin dans l'alphabet prime ; les suffixes les plus récents priment.** Le CLI recopie tout fichier nouveau ou plus récent dans architecture/spec_v2/. Source de vérité de la descente : skill partagé transcriptstudio-spec (v39).

| Document | Fichier courant | Phase |
|---|---|---|
| Feuille de route | FEUILLE_DE_ROUTE_V2_2026-10-30d.md | toutes |
| Contrat du format étude | **CONTRAT_FORMAT_ETUDE_V2_2026-10-29.md** | P14 |
| Spécification moteur | SPEC_MOTEUR_P15_V2_2026-10-27.md | P15.3/P15.4 |
| Spec UI Reformulation | UI_REFORMULATION_V2_2026-10-27b.md | P16 |
| **Correctifs UI Reformulation (séries 1-4)** | **UI_REFORMULATION_MODIFS_V2_2026-10-30f.md** | **P16-bis** |
| **Paramétrage LLM** | **PARAMETRAGE_LLM_V2_2026-10-31c.md** | **P15** |
| **Gestion des prompts (bibliothèque + éditeur)** | **UI_GESTION_PROMPTS_V2_2026-10-31a.md** | **P16-ter** |
| Addendum Bibles | BIBLE_JND_V2_2026-10-28b.md | P18.5 |
| Spec navigation (hub, Réunion, Étude, Ouvrage) | SPEC_NAVIGATION_V2_2026-10-29b.md | P18.6 |
| **Correctifs de relecture navigation (séries 1-8)** | **SPEC_NAVIGATION_MODIFS_V2_2026-10-31e.md** | **P18.6-bis** |
| Prompt reformulation v2 | PROMPT_REFORMULATION_V2.md | P16 |
| Prompt résumé v2 | PROMPT_RESUME_V2.md | P17 |
| Workflow (schémas) | WORKFLOW_V2_2026-10-27.md | — |
| Arbitrage P14 | ARBITRAGE_P14.md | clos |
| Arbitrage P15 | ARBITRAGE_P15.md | clos |
| Arbitrage création d'étude | ARBITRAGE_CREATION_ETUDE.md | correctif P14.3 |
| Arbitrage exclusivité réunions/études | ARBITRAGE_EXCLUSIVITE_REUNIONS_2026-10-29.md | P18.6 |
| **Arbitrage P19.4 fusions/régénération** | **ARBITRAGE_P19_4_FUSION_REGENERATION_2026-11-07a.md** | **P19.4 — VALIDÉ** |
| **Arbitrage prompt de fusion (bibliothèque éditable)** | **ARBITRAGE_PROMPT_FUSION_2026-11-07a.md** | **P19.4-bis — VALIDÉ** |

Rappel (David, 2026-10-28) : version Bible **par défaut = darbyR (Darby révisée)**. **Reste à faire : recette humaine P16/P17/P18/P18.6/P19 par David** (checklist fin de session P17 du PROJECT_STATE), puis P20 : détection des pensées similaires, sous-titres IA, aides à la relecture, export DOCX structuré. P19 est clos côté spécification.