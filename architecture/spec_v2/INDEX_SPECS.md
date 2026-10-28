# INDEX_SPECS — documents de spécification TranscriptStudio v2

Mis à jour : 2026-10-27 (atelier, 3ᵉ série de correctifs UI). **Règle : un document suffixé par une date prime sur son homonyme non suffixé ; en cas de plusieurs suffixes le même jour (b, c, d…), la lettre la plus loin dans l'alphabet prime.** Le CLI recopie tout fichier nouveau ou plus récent dans architecture/spec_v2/. Source de vérité de la descente : skill partagé `transcriptstudio-spec`.

| Document | Fichier courant | Phase |
|---|---|---|
| Feuille de route | FEUILLE_DE_ROUTE_V2_2026-10-27d.md | toutes |
| Contrat du format étude | CONTRAT_FORMAT_ETUDE_V2_2026-10-27.md | P14 |
| Spécification moteur | SPEC_MOTEUR_P15_V2_2026-10-27.md | P15.3/P15.4 |
| Spec UI Reformulation | UI_REFORMULATION_V2_2026-10-27b.md | P16 |
| **Spec UI correctifs de relecture (séries 1 à 3)** | **UI_REFORMULATION_MODIFS_V2_2026-10-27d.md** | **P16-bis — prime sur la précédente pour ses points** |
| Spec paramétrage LLM | PARAMETRAGE_LLM_V2.md | P15.1/P15.2 |
| Prompt reformulation v2 | PROMPT_REFORMULATION_V2.md | P16 |
| Prompt résumé v2 | PROMPT_RESUME_V2.md | P17 |
| Workflow (schémas) | WORKFLOW_V2_2026-10-27.md | — |
| Arbitrage P14 | ARBITRAGE_P14.md | clos |
| Arbitrage P15 | ARBITRAGE_P15.md | clos |
| Arbitrage création d'étude | ARBITRAGE_CREATION_ETUDE.md | correctif P14.3 |

3ᵉ série (relecture du 2026-10-27, §15-18) : lecteur audio sain au retour sur la page (arrêt propre en quittant, réinitialisation jouable au retour) ; **aucune lecture automatique au clic/double-clic — seul le bouton lecture/pause joue** ; clé API LLM persistée dans le CredentialStore avec UX identique à ElevenLabs (•••••• masqués, test sans ressaisie, survit au redémarrage) ; éditeur de catalogue strictement lié à la sélection (listes de modèles par fournisseur sans mélange ni doublons, panneau d'édition = modèle sélectionné du fournisseur courant, fournisseurs par défaut préremplis).

Prochaine session CLI : **P16-bis complet** (séries 1 à 3) + ARBITRAGE_CREATION_ETUDE.md + renommage UI « réunion ».