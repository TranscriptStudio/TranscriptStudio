# Arbitrage — Prompt de fusion dans la bibliothèque éditable (P19.4-bis)

**Statut : VALIDÉ par l'atelier de spécification — fait autorité.**
Date : 2026-11-07 (suffixe a). Répond à la question du CLI : le prompt de fusion assistée (P19.4) est codé en dur dans l'app ; faut-il l'ajouter aux prompts éditables ?

## 1. Décision

**OUI.** Le prompt de fusion devient un usage de la bibliothèque P16-ter, fichier `prompts/fusion.md`, au même titre que reformulation et résumé. Règle générale désormais explicite : **tout prompt envoyé à un LLM par l'app vit dans la bibliothèque `prompts/<usage>.md`** — aucun prompt utilisateur-invisible codé en dur.

## 2. Conditions (reprendre telles quelles les règles P16-ter de UI_GESTION_PROMPTS_V2_2026-10-31a.md)

- Fichier en **texte brut (.md), mode source uniquement**, pas d'éditeur riche.
- Visible et éditable depuis **⚙ Prompts** (page Reformulation et page Résumé), entrée « Fusion ».
- **Mode étude** : copie locale par étude, promulgation/rechargement explicites — l'édition locale ne modifie jamais la bibliothèque globale.
- **Traçabilité texte + hash** par version : chaque fusion assistée enregistre le texte du prompt utilisé et son hash dans ouvrage.json (même mécanique que P19.4 pour les provenances).
- L'usage apparaît au catalogue avec un libellé explicite (« Fusion de pensées ») et, comme pour les autres usages, l'app fournit toujours un prompt par défaut reconstituable si le fichier est supprimé.

## 3. Paramètres

Le prompt reçoit les pensées candidates (textes, locuteurs, réunions sources). Le découpage en variables suit la convention des autres prompts (`{{...}}`). La proposition LLM reste **toujours éditable et jamais auto-appliquée** (inchangé, P19.4).

## 4. Migration

À la livraison : créer `prompts/fusion.md` avec le texte actuel codé en dur comme contenu initial ; l'app lit ensuite uniquement le fichier. Une étape, un commit.

## 5. Versioning

Correctif désigné **P19.4-bis**. Ce document prime sur toute interprétation antérieure. Le CLI recopie ce fichier dans architecture/spec_v2/. Peut être livré dans le même run que la série 8 (§31) de SPEC_NAVIGATION_MODIFS_V2_2026-10-31e.md ou juste après.
