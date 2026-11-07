# Correctifs — Relance ciblée sur sélection (Reformulation & Résumé)

**Statut : SPEC D'ATELIER — fait autorité pour ses points.**
Date : 2026-11-07 (suffixe a). Découverte : test humain de David sur le résumé (retravailler la sélection du dernier paragraphe avec consigne « traduire en français » → tout le résumé a été remplacé par un texte neuf, plus long, toujours en anglais).

## 1. Diagnostic (constaté dans le code)

Deux défauts de conception dans la relance ciblée, identiques dans `services/traitements/resume.py` (relancer_selection) et `services/traitements/moteur.py` (assembler_contexte + traiter_bloc avec selection) :

- **D1 — la sélection n'est jamais envoyée.** Le message LLM ne contient que les offsets (« offsets caractères 2345 à 2612 »). Un LLM ne compte pas les caractères : il ne sait pas quel passage viser. La consigne « retravailler uniquement le passage délimité » est donc inopérante.
- **D2 — le LLM doit réécrire le document entier.** L'instruction finale demande « le résumé complet, retravaillé partiellement », avec en contexte la source complète + toutes les versions antérieures. Le modèle régénère donc un résumé neuf de bout en bout : le reste du texte n'est PAS conservé, la longueur cible est relue sur la source (d'où un texte différent et plus long), et la consigne (traduction) est noyée/diluée dans les instructions de résumé dominantes — d'où son ignorance.

## 2. Sémantique corrigée (règle générale)

**La relance ciblée retravaille UNIQUEMENT le passage sélectionné, et c'est l'APPLICATION qui racorde, pas le LLM.**

- **Inv. S1 (périmètre)** : le message LLM contient le TEXTE du passage sélectionné (pas des offsets). Le LLM doit retourner UNIQUEMENT le passage retravaillé — aucun préambule, aucun commentaire, aucun texte hors passage.
- **Inv. S2 (raccord applicatif)** : l'application remplace programmatiquement la tranche [debut, fin] dans le texte courant par la réponse (strippée des espaces parasites). Tout le reste du texte est conservé **octet pour octet** — garanti par construction, pas par la discipline du modèle.
- **Inv. S3 (consigne primes)** : la consigne est énoncée en dernier, explicitement prioritaire : « Retravailler ce passage selon cette consigne : <consigne>. Répondre uniquement par le passage retravaillé. » Une consigne peut changer la langue (ex. traduire en français) : elle prime sur toute habitude de langue du prompt système.
- **Inv. S4 (contexte minimal, en lecture seule)** : pour la cohérence stylistique, le message peut inclure le texte courant complet (ou le titre + paragraphes voisins), marqué « pour contexte seulement — ne pas reproduire, ne pas retravailler ». On ne renvoie PAS la source ni les versions antérieures dans la relance ciblée (coût divisé, et c'est ce qui causait la régénération).
- **Inv. S5 (version)** : le texte complet assemblé (inchange hors passage + passage retravaillé) est consigné comme nouvelle version, origine `relance_ciblee`, avec la consigne et les stats ; l'historique et le retour arrière protègent l'utilisateur inchangés.

## 3. Points d'implémentation

1. **Résumé (`ServiceResume.relancer_selection`)** : reconstruire le message — passage sélectionné + consigne + contexte texte courant en lecture seule ; remplacer la tranche ; consigner.
2. **Reformulation (`MoteurTraitements`)** : même correction dans `_message`/`assembler_contexte`/`traiter_bloc` — le passage sélectionné du texte courant du bloc est envoyé, la réponse remplace la tranche, la fenêtre glissante reste utilisable pour le style.
3. **Garde-fou léger** : réponse vide → erreur propre (message : le modèle n'a rien produit, rien n'est consigné). Réponse dont la longueur dépasse largement le passage (ex. > 3×) : accepter mais marquer la version (« réponse plus longue que le passage, vérifier ») — le retour arrière reste le filet.
4. La sélection continue d'être stockée dans la version (debut/fin + texte), inchangé.
5. Les tests existants de relance ciblée (reformulation et résumé) doivent être adaptés à la nouvelle sémantique : le message envoyé contient le passage et non les offsets seuls ; la réponse du client factice est insérée à la tranche ; le reste inchangé.

## 4. Ce qui ne change pas

Relance complète avec consigne, génération, édition manuelle, versioning, validation, page ③ Résumé (série 8) : aucun changement de comportement.
