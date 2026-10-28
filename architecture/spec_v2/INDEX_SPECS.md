# INDEX_SPECS — documents de spécification TranscriptStudio v2

Mis à jour : 2026-10-28 (atelier, correction défaut Bible = Darby révisée). **Règle : un document suffixé par une date prime sur son homonyme non suffixé ; en cas de plusieurs suffixes le même jour, la lettre la plus loin dans l'alphabet prime ; les documents du 2026-10-28 priment sur ceux du 2026-10-27.** Le CLI recopie tout fichier nouveau ou plus récent dans architecture/spec_v2/. Source de vérité de la descente : skill partagé `transcriptstudio-spec` (v20).

| Document | Fichier courant | Phase |
|---|---|---|
| Feuille de route | FEUILLE_DE_ROUTE_V2_2026-10-28b.md | toutes |
| Contrat du format étude | CONTRAT_FORMAT_ETUDE_V2_2026-10-27.md | P14 |
| Spécification moteur | SPEC_MOTEUR_P15_V2_2026-10-27.md | P15.3/P15.4 |
| Spec UI Reformulation | UI_REFORMULATION_V2_2026-10-27b.md | P16 |
| Spec UI correctifs de relecture (séries 1-3) | UI_REFORMULATION_MODIFS_V2_2026-10-27d.md | P16-bis (livré) |
| Spec paramétrage LLM | PARAMETRAGE_LLM_V2.md | P15.1/P15.2 |
| **Addendum Bibles** | **BIBLE_JND_V2_2026-10-28b.md** | **P18.5** |
| Prompt reformulation v2 | PROMPT_REFORMULATION_V2.md | P16 |
| Prompt résumé v2 | PROMPT_RESUME_V2.md | P17 |
| Workflow (schémas) | WORKFLOW_V2_2026-10-27.md | — |
| Arbitrage P14 | ARBITRAGE_P14.md | clos |
| Arbitrage P15 | ARBITRAGE_P15.md | clos |
| Arbitrage création d'étude | ARBITRAGE_CREATION_ETUDE.md | correctif P14.3 |

**Correction (David, 2026-10-28)** : la version Bible **par défaut est `darbyR` (Darby révisée)** — la version `darby` reste disponible au téléchargeur et sélectionnable par étude.

Prochaine session CLI : **P18.5** selon BIBLE_JND_V2_2026-10-28b.md — téléchargeur de Bibles intégré (Darby / Darby révisée / Segond 1910, jamais commité) + version retenue par étude (**défaut `darbyR`**) + gestion des versifications différentes (écart = information, pas d'automatisme). Numéros Strong hors v2.