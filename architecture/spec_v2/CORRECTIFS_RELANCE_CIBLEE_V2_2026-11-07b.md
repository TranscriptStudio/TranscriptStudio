# Correctifs — Relance ciblée sur sélection, série 2 : anti-résidu de la réponse

**Statut : SPEC D'ATELIER — fait autorité pour ses points. Prime sur CORRECTIFS_RELANCE_CIBLEE_V2_2026-11-07a.md pour ses points.**
Date : 2026-11-07 (suffixe b). Découverte : test humain de David — après application du correctif série 1, « retravailler la sélection » du dernier paragraphe avec consigne « traduire en français » produit le bon résultat global (passage traduit, reste du document intact au caractère près), MAIS un fragment du texte original est resté dupliqué dans le passage retravaillé : la phrase française complète est suivie de sa fin non traduite (« …avec les ordinateurs. » puis « technical ground to cover before he could work independently with computers. »).

## 1. Diagnostic

Le raccord applicatif (inv. S2) fonctionne : le reste du texte est conservé octet pour octet. Le défaut est dans la **proprete de la réponse du LLM** : le modèle a retourné le passage retravaillé suivi d'un fragment du texte original (queue non traduite de la phrase). Le contexte contenant le texte original du passage, le modèle l'a partiellement reproduit. Le garde-fou « réponse > 3× le passage » ne s'est pas déclenché (réponse ~2×), et rien ne détecte un résidu non retravaillé.

## 2. Règles complémentaires (inv. S6/S7/S8)

- **Inv. S6 (instruction anti-reproduction)** : le message doit contenir, en dernier, une instruction explicite : « Répondre UNIQUEMENT par le passage retravaillé, complet (du premier au dernier mot du passage), sans préambule, sans commentaire, et sans reproduire aucun fragment du texte original. »
- **Inv. S7 (garde anti-résidu)** : après réponse, l'application vérifie si la réponse contient une sous-chaîne de **6 mots consécutifs ou plus** présente dans le passage original (comparaison normalisée : minuscules, espaces/retours ramenés à un espace, ponctuation ignorée). Si oui → le résidu est signalé : la version est consignée (le retour arrière reste le filet) mais l'UI affiche un avertissement clair : « La réponse contient un fragment du texte original — vérifiez la zone retravaillée. » Jamais de blocage, jamais de modification automatique de la réponse.
- **Inv. S8 (cohérence de périmètre)** : le passage envoyé au LLM doit être le texte exact de la tranche [debut, fin] telle qu'elle sera remplacée — pas une version tronquée ou résumée — pour que le modèle sache précisément où s'arrêter (la duplication observée vient aussi d'une frontière floue pour le modèle).

## 3. Périmètre

Mêmes sites que la série 1 : relance ciblée du résumé (ServiceResume.relancer_selection) et relance ciblée par bloc (MoteurTraitements). Tests : réponse contenant un résidu → avertissement affiché, version consignée ; réponse propre → aucun avertissement ; la détection est testée sur les deux services.

## 4. Rappel de synchro

La session d'application du correctif série 1 (et celle-ci) doivent figurer dans PROJECT_STATE et être poussées sur origin/v2 : au moment du test, le fichier services/traitements/resume.py visible sur la branche v2 distante était encore l'ancienne version (offsets + régénération complète).
