# INDEX_SPECS — documents de spécification TranscriptStudio v2

Mis à jour : 2026-10-31i (atelier). Série 8 navigation (31e) : fusion de l'outillage du résumé dans la page Résumé — suppression de la fenêtre « Résumé... ».  Nouveau : UI_GESTION_PROMPTS_V2_2026-10-31a.md — bibliothèque de prompts éditable (.md), bouton ⚙ Prompts sur les pages Reformulation/Résumé, copie locale par étude + promulgation explicite.  Série 7 navigation (31d) : balayage lumineux unique au survol des pastilles CLIQUABLES du stepper (page Réunion uniquement), teinte adaptée à l'état ; aucune animation sur les pastilles sans lien (hub, page Étude).  Ajouts : échelles d'effort par modèle (Mistral Large 4 low/medium/high ; Claude low/medium/high/xhigh/max via output_config ; GLM low/high/max) ; Ajout : effort de raisonnement configurable (reasoning_effort low/medium/high, défaut high pour Le Chonk) ; Mistral Large 4 « Le Chonk » au catalogue LLM. Ajout : Mistral Large 4 « Le Chonk » au catalogue LLM (mistral-large-4, contexte 1 M, température OK, prix 0,70/2,10 $/M). Série 6 navigation : Série 6 navigation : pastilles uniformisées (non configuré = gris off, rouge = échec réel uniquement), aucune mention pour les non-transcrites sur le hub.  Nouveauté : 4ᵉ série UI Reformulation — barre de progression par blocs + temps écoulé et estimation restante lors de la reformulation, cas N = 1 bloc (temps seul). Aussi : correctifs P18.6-bis, séries 1-5 : stepper après transcription, bouton unique, tuile Études = menu déroulant direct, tuiles avec contours visibles et effet de survol, série 5 = couleurs affirmées (accent bleu vif #3b9eff, stepper #2563eb/émeraude #2ec98a), hub v4 (plaque métal brossé, tuiles de réunion cliquables) et correctifs techniques (angle du menu Études, fonds de zones de texte, plein écran par défaut). **Règle : un document suffixé par une date prime sur son homonyme non suffixé ; en cas de plusieurs suffixes le même jour, la lettre la plus loin dans l'alphabet prime ; les documents du 2026-10-30 priment sur ceux du 2026-10-29, qui priment sur ceux du 2026-10-28.** Le CLI recopie tout fichier nouveau ou plus récent dans architecture/spec_v2/. Source de vérité de la descente : skill partagé `transcriptstudio-spec` (v39).

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
| **Arbitrage exclusivité réunions/études** | **ARBITRAGE_EXCLUSIVITE_REUNIONS_2026-10-29.md** | **P18.6** |

Rappel (David, 2026-10-28) : version Bible **par défaut = `darbyR` (Darby révisée)**. Prochaine session CLI : **P18.6** selon SPEC_NAVIGATION_V2_2026-10-29b.md, CONTRAT_FORMAT_ETUDE_V2_2026-10-29.md (invariant 13.5 réécrit) et FEUILLE_DE_ROUTE_V2_2026-10-29.md. La recette humaine P16/P17/P18 par David (checklist fin de session P17 du PROJECT_STATE) reste en attente — avant ou après P18.6, à la convenance de David. Ensuite P19/P20 (v2.1).