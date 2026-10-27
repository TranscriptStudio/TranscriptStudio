# ARBITRAGE ATELIER — P14 (2026-10-27)

> Décisions de l'atelier de spécification sur les points soumis dans
> PROJECT_STATE.md (session P14). Ce document prime sur tout désaccord
> éventuel avec les autres documents de ce dossier.

## Validation globale

**P14.1 à P14.4 : VALIDÉS.** 93 tests verts, règles d'invariance couvertes,
code additif sans régression v1 : exactement ce que l'atelier attendait.
Le CLI peut poursuivre.

## Arbitrages sur les points soumis

1. **Champ `chemin_absolu` (réunions/<nom>.json)** : VALIDÉ, devient
   contractuel. Le contrat v2 (skill transcriptstudio-spec v11) l'intègre
   désormais explicitement.
2. **Champ `buffer` (opérations silence_supprime du journal)** : VALIDÉ,
   devient contractuel. Intégré au contrat v2.
3. **Sémantique des frontières de conversion** (position dans la partie
   supprimée → début de coupe ; frontière exacte → début de la partie
   supprimée) : VALIDÉE. Choix conservateur et déterministe ; les deux côtés
   d'une coupe partageant la même position traitée est le bon comportement
   pour un repérage audio.
4. **Doublon refusé au sein d'une même étude** : VALIDÉ. La règle du contrat
   (pas de doublon *entre* réunions d'une étude) est l'interprétation juste ;
   l'ambiguïté FID/titres en serait une raison suffisante.
5. **Journal écrit en fin de traitement** : VALIDÉ.
6. **Signaux de sous-découpage réduits** (fin de phrase + pause du discours
   originel + marqueurs de transition + interdiction de couper dans une
   citation) : VALIDÉS pour P14. Les signaux « fin de paragraphe » et
   « changement de référence biblique » sont reportés naturellement : le
   premier dépend du format v1 (pas de marqueurs), le second du parsing JND
   (P18). Note pour P18 : une fois le parsing de références disponible,
   évaluer l'ajout du signal « changement de référence » au scoring.
7. **Navigation Étude → éditeur v1** (fenêtre séparée, Accueil général) :
   ACCEPTÉE pour P14 — à revoir en P16 lors de la page Reformulation, où la
   navigation entre étude, réunion et traitement devra être cohérente.
8. **README / manuel** : reportés à la première livraison visible (P16 ou
   export v2) — VALIDÉ.
9. **resources/prompts/ dans le prochain build packaging** : noté, aucune
   action avant un build v2.

## Suite recommandée

1. **P14.5** (fusion de blocs : FID sources, attribution multiple,
   réversibilité ; + ordre d'ouvrage par réunion) pour clore P14.
2. Puis **P15** — service LLM multi-fournisseurs
   (spec : PARAMETRAGE_LLM_V2.md, dans le skill et ce dossier).

Le contrat v2 (v11) incorpore les champs validés aux points 1 et 2.
