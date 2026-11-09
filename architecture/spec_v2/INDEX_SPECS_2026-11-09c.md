# INDEX_SPECS — documents de spécification TranscriptStudio v2

Mis à jour : 2026-11-09c (atelier, rév. 5). **Décision David du 09/11 : P20 reste dans la V2 — plus de v2.1.** La v2 ne sera close qu'après livraison et recette de P20 (P20.1 mobilité des paragraphes, P20.2 sous-titres IA, P20.3 aides à la relecture, P20.4 export DOCX structuré, P20.5 référence de contrôle qualité par portée — sélecteur dans le volet Réunion persisté au tier + référence d'uniformité au niveau ouvrage jamais réécrite vers les tiers, §8bis du CONTRAT_STOCKAGE_REUNIONS —, P20.6 synthèse d'étude repensée, et retrait de la compatibilité FID nu). Recette humaine P14 → P19 : OK le 09/11 (709 tests verts). Décisions David du 09/11 : registre global des études REFUSÉ (clos) ; P18.4 pré-correction ABANDONNÉE DÉFINITIVEMENT ; P20.5 ajouté ; **relecture du soir (page Étude, 9 points) : P18.9 correctifs page Étude (glisser-déposer des tuiles, clic droit, badge Bible simplifié, « Édition ouvrage final », fonds, scroll) + P20.6 synthèse d'étude repensée (manuelle, incrémentale, prompt éditable prompts/synthese_etude.md, redondances dans la page Ouvrage) consignés — SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_2026-11-09d ; récurrences exclusivement dans la page Ouvrage (amendement P20.3) ; 4 arbitrages actés (clic gauche = déplacement uniquement ; injection de contexte conservée ; ré-alimentation = remplacement avec avertissement ; redondances = présélection locale + confirmation LLM)**. **P18.10 lecteur de Bible intégré ajouté (décision David du 09/11 soir) : page consultative accessible depuis les pages Réunion, transcription et Ouvrage ; sélecteurs version/livre/chapitre/verset pilotés par l'OSIS ; dernier passage mémorisé dans les réglages ; version par défaut = dernière consultée ; saisie directe de référence normalisée P18.1 ; aucune écriture hors réglages (BIBLE_JND_V2 §7, invariants 6-9)**. **Plus aucun arbitrage en attente.** **Règle : un document suffixé par une date prime sur son homonyme non suffixé ; en cas de plusieurs suffixes le même jour, la lettre la plus loin dans l'alphabet prime ; les suffixes les plus récents priment.** Le CLI recopie tout fichier nouveau ou plus récent dans architecture/spec_v2/. Source de vérité de la descente : skill partagé transcriptstudio-spec (v43).

| Document | Fichier courant | Phase |
|---|---|---|
| Feuille de route | **FEUILLE_DE_ROUTE_V2_2026-11-09c.md** | toutes |
| Contrat du format étude | CONTRAT_FORMAT_ETUDE_V2_2026-10-29.md | P14 |
| Contrat stockage réunion (P18.7) | CONTRAT_STOCKAGE_REUNIONS_V2_2026-11-09a.md | P18.7 — LIVRÉ, prime sur le contrat format étude |
| Spécification moteur | SPEC_MOTEUR_P15_V2_2026-10-27.md | P15.3/P15.4 |
| Spec UI Reformulation | UI_REFORMULATION_V2_2026-10-27b.md | P16 |
| Correctifs UI Reformulation (séries 1-4) | UI_REFORMULATION_MODIFS_V2_2026-10-30f.md | P16-bis |
| Paramétrage LLM | PARAMETRAGE_LLM_V2_2026-10-31c.md | P15 |
| Gestion des prompts (bibliothèque + éditeur) | UI_GESTION_PROMPTS_V2_2026-10-31a.md | P16-ter |
| Addendum Bibles + lecteur de Bible | BIBLE_JND_V2_2026-11-09d.md | P18.5 + P18.9c + P18.10 (lecteur intégré) |
| Spec navigation (hub, Réunion, Étude, Ouvrage) | SPEC_NAVIGATION_V2_2026-10-29b.md | P18.6 |
| Correctifs de relecture navigation (séries 1-8) | SPEC_NAVIGATION_MODIFS_V2_2026-10-31e.md | P18.6-bis |
| Correctifs page Étude & synthèse repensée | SPEC_PAGE_ETUDE_ET_SYNTHESE_MODIFS_2026-11-09d.md | P18.9 + P20.6 — prime sur specs navigation pour les points traités |
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
| Arbitrage écarts P18.7 | ARBITRAGE_P18_7_ECARTS_2026-11-09a.md | P18.7 — conformité ACTÉE |

Rappel (David, 2026-10-28) : version Bible **par défaut = darbyR (Darby révisée)** — la versification n'est plus affichée séparément (P18.9c).
