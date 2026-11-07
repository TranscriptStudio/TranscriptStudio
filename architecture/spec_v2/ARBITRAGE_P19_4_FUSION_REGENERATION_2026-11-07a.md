# Arbitrage P19.4 — Fusions et régénération de l'ouvrage

**Statut : VALIDÉ par l'atelier de spécification — fait autorité.**
Date : 2026-11-07 (suffixe a). Répond à la question soumise par le CLI dans le PROJECT_STATE du 07/11 (P19.4 livré, interprétation à confirmer).

## 1. Question soumise

Après une fusion de pensées (P19.4, manuelle ou assistée LLM), que devient le paragraphe fusionné si l'ouvrage est régénéré ? Le CLI proposait : « les paragraphes fusionnés survivent aux régénérations comme toute édition d'ouvrage ».

## 2. Décision

**L'interprétation du CLI est VALIDÉE sans réserve.** Une fusion est une **édition du document dérivé** (ouvrage.json), au même titre que toute modification manuelle du texte. Elle n'est jamais défaite automatiquement.

Invariants qui en découlent :

- **Inv. A (persistance)** : aucune opération automatique (re-transcription, re-reformulation, re-résumé d'une réunion source, etc.) ne défait ni ne modifie une fusion existante. La composition d'ouvrage reste uniquement le fruit d'éditions explicites.
- **Inv. B (régénération explicite)** : seule la **régénération explicite de l'ouvrage** (P19.3) peut faire disparaître une fusion, puisqu'elle écrase le document dérivé ; l'avertissement existant de P19.3 (« cette opération écrase les éditions de l'ouvrage, y compris les fusions ») doit le mentionner clairement. Aucune perte silencieuse.
- **Inv. C (traçabilité conservée)** : après une fusion, les provenances multiples (FIDs, locuteurs, réunions) restent enregistrées dans ouvrage.json et consultables ; la dé-fusion reste réversible tant que l'historique n'est pas écrasé par une régénération.

## 3. Justification

C'est exactement la sémantique de l'**instantané éditable** posée par P19.1 : ouvrage.json est un document dérivé, figé à la génération, puis souverain face à ses sources tant que l'utilisateur ne régénère pas explicitement. Toute autre lecture (recollage automatique des fusions à chaque régénération) casserait la prévisibilité et l'invariant « composition d'ouvrage uniquement ».

## 4. Report

La **détection automatique des pensées similaires** (suggestion de fusions candidates) est confirmée en **P20**, comme proposé. P19 reste complet en l'état.

## 5. Versioning

Ce document prime sur toute interprétation antérieure pour les points couverts. Le CLI recopie ce fichier dans architecture/spec_v2/.
