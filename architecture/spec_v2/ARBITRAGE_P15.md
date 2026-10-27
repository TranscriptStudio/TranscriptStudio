# ARBITRAGE_P15 — retour de l'atelier sur P15.1/P15.2 (et arbitrages moteur P15.3/P15.4)

Date : 2026-10-27 · Publié par l'atelier de conception · Fait foi pour la suite de P15.

## 1. Réponses aux 7 points soumis par le CLI (P15.1/P15.2) — TOUS VALIDÉS

1. **Infos de compte** (validité de la clé + nombre de modèles) : OK — afficher quand l'API l'expose.
2. **Clé mémorisée lors d'un changement de fournisseur** : OK.
3. **Invariant 4** (échec d'appel sans modification des documents) : OK — un test unitaire dédié est exigé.
4. **Heuristique 4 caractères/token** pour l'estimation de coût : OK, à défaut de tokenizer exact.
5. **include_usage conditionnel** (selon support du streaming par l'API) : OK.
6. **Adjacence des blocs pour la fusion** : OK.
7. **UI fusion/ordre d'ouvrage** : reporté à P16 comme convenu.

## 2. Décisions David (2026-10-27) intégrées aux specs

- **B1 — Confirmation des coûts** : affichage du coût faisant office de confirmation **pour la première passe totale uniquement** (estimation avant, coût réel affiché en fin de passe) ; **aucune confirmation** pour les reformulations par bloc.
- **B1bis — Log des opérations** (nouveau, remplace le « journal de passe » de P15.4) : fichier dédié `traitements/journal_operations.json` dans l'étude, append-only, généralisé à tout le process (passes, reformulations, relances, éditions, validations, fusions, erreurs API, annulations) ; page in-app « 📋 Log » en lecture seule depuis la barre supérieure. Contrat : CONTRAT_FORMAT_ETUDE_V2 §11 ; comportement : SPEC_MOTEUR_P15_V2 §5 ; UI : UI_REFORMULATION_V2 §8.
- **B2 — Annulation à mi-passe** : tout ce qui est déjà produit est conservé ; la reprise saute les blocs traités.
- **B3 — Aucune cascade** : suppression de la proposition de reprise des blocs suivants après validation ; l'utilisateur relance individuellement les blocs qu'il veut.
- **C1 — Débordement de contexte** : troncation par le haut (blocs les plus anciens de la fenêtre glissante d'abord) ; jamais la synthèse d'étude, jamais l'unité courante.
- **C2 — Températures** : par défaut dans les **réglages de l'app** (reformulation **0.3**, résumé **0.2**) avec texte d'aide expliquant les effets ; **surcharge possible au niveau de l'étude** (parametres.json) ; jamais codées en dur dans le moteur.

## 3. Nouveau document d'autorité

**SPEC_MOTEUR_P15_V2.md** : spécification complète du moteur P15.3/P15.4 (assemblage de contexte et troncation, températures, exécution, annulation, reprise, défaillance API, aucune cascade, log des opérations, 6 règles d'invariance). À suivre pour l'implémentation de P15.3/P15.4.

## 4. Correction Git à exécuter en début de prochaine session

Le push accidentel de P14 sur `origin/master` doit être réécrit : `git push --force-with-lease origin master` (master local est déjà revenu à v1). À faire AVANT tout nouveau commit sur master.

## 5. Périmètre de la prochaine session CLI

P15.3 (moteur de traitement) + P15.4 (log des opérations), selon SPEC_MOTEUR_P15_V2.md, CONTRAT_FORMAT_ETUDE_V2.md (§7, §10, §11) et UI_REFORMULATION_V2.md (§8, page Log, si reachable dans cette phase ; sinon la page Log peut suivre en P16).
