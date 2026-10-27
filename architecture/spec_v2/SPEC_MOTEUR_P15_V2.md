
# Spécification du moteur de traitement (P15.3 / P15.4)

Ce document fait autorité pour l'implémentation du moteur de traitement (P15.3) et du log des opérations (P15.4, qui remplace l'ancien « journal de passe »). Toute divergence constatée en développant se signale dans PROJECT_STATE.md et s'arbitre à l'atelier. Il complète : le contrat du format étude (stockage), la spécification du paramétrage LLM (P15.1/P15.2), la spec UI Reformulation (P16).

## 1. Rôles et périmètre

Le moteur (`services/traitements/`) orchestre l'exécution des blocs (Reformulation en P15 ; Résumé en P17) :

1. **Assemblage du contexte** de chaque appel LLM (§2) ;
2. **Exécution séquentielle** des unités dans l'ordre chronologique (§3) ;
3. **Stockage** des résultats versionnés (contrat format étude §7/§8) ;
4. **Log des opérations** (§5) — toute opération, tout le process ;
5. Contrôle qualité local (hors périmètre P15.3, livré en P16.4/P18).

Le moteur est agnostique du bloc : assemblage, exécution, annulation, reprise et log sont communs ; seuls prompt système, périmètre de l'unité et paramètres (température…) varient.

## 2. Assemblage du contexte (par appel)

Ordre d'assemblage du prompt envoyé : prompt système du bloc → synthèse d'étude (si cochée, ≤ ~1 500 tokens) → fenêtre glissante → unité courante → consigne libre éventuelle (relances).

- **Fenêtre glissante** (≤ ~2 000 tokens, paramétrable) : N derniers résultats **produits** pendant une passe complète (frais, non validés) ; N derniers résultats **validés** lors des relances/reprises. Le contexte utilisé est consigné dans la version (`contexte`, contrat §7).
- **Budget explicite** : le moteur additionne prompt + synthèse + fenêtre + unité avant l'appel et vérifie la fenêtre maximale du modèle (catalogue P15.1).

### 2.1 Débordement de contexte — troncation par le haut (décision David 2026-10-27)

Si le total dépasse la fenêtre du modèle, la troncation s'applique **dans cet ordre, jusqu'à tenir** :

1. retirer de la fenêtre glissante **les blocs les plus anciens en premier** (on conserve les plus récents) ;
2. **jamais** la synthèse d'étude, **jamais** l'unité courante, **jamais** le prompt système ;
3. si l'unité courante seule + prompt dépasse la fenêtre : erreur propre, bloc signalé (l'unité doit passer par sous-découpage, cas déjà couvert par P14.4 pour les monologues longs).

Conséquence assumée : sur très longues études, la cohérence de style repose sur la synthèse plutôt que sur la mémoire des blocs anciens.

### 2.2 Températures (décision David 2026-10-27)

- Valeurs **par défaut dans les réglages de l'app** : reformulation **0.3**, résumé **0.2** ; chacune avec un texte d'aide court expliquant les effets (basse = sobre et fidèle ; haute = plus libre) ;
- **surcharge possible au niveau de l'étude** : `parametres/parametres.json` (contrat §10) porte `temperature` par bloc, initialisé depuis les réglages de l'app ;
- le paramètre n'est envoyé à l'API que si le modèle le supporte (capacités du catalogue P15.1).

## 3. Exécution séquentielle et annulation

### 3.1 Lancement et confirmation des coûts (décision David B1, 2026-10-27)

- **Première passe totale uniquement** : estimation du coût puis affichage du coût réel en fin de passe — cet affichage **fait office de confirmation** de la passe suivante ; pas de boîte de dialogue de confirmation supplémentaire ;
- **toutes les reformulations par bloc** (relances complètes, ciblées, passes partielles) : **pas de confirmation**, exécution directe ;
- l'estimation utilise le catalogue de coûts des réglages de l'app.

### 3.2 Annulation en cours de passe (décision David B2, 2026-10-27)

- l'annulation **arrête proprement** l'exécution à la fin de l'appel LLM en cours (l'appel en vol n'est pas tué à mi-réponse, son résultat est conservé s'il aboutit) ;
- **tout résultat déjà produit est conservé** (versionné normalement) ; rien n'est effacé ;
- la barre d'état indique « passe interrompue — N blocs traités ».

### 3.3 Reprise après interruption

- relancer une passe sur une réunion **saute les blocs déjà traités** (possédant un résultat non suivi d'une édition) et reprend au premier bloc sans résultat ; pas de re-traitement silencieux ;
- un bloc dont l'utilisateur veut refaire le traitement passe par la relance explicite (menu pastille).

### 3.4 Défaillance API

- erreurs réseau/API : retry (P15.1) puis, à l'échec définitif, **arrêt propre de la passe** (pas d'arrêt brutal ni de corruption) ;
- l'erreur est consignée au log des opérations (§5) avec le message du fournisseur ;
- les résultats déjà produits sont conservés ; la reprise suit §3.3.

## 4. Aucune cascade (décision David B3, 2026-10-27)

- après validation d'un bloc, **aucune proposition de reprise automatique des blocs suivants** ;
- l'utilisateur relance individuellement les blocs qu'il veut retoucher via le menu pastille (spec UI §5) ;
- le moteur ne fournit que la commande explicite « traiter les blocs non validés ».

## 5. Log des opérations (P15.4)

Remplace l'ancien « journal de passe ». Fichier **dédié associé à l'étude** : `traitements/journal_operations.json` (contrat format étude §11). Il journalise **toutes les opérations du process**, pas seulement les passes LLM.

### 5.1 Entrées consignées

Chaque entrée porte : `horodatage`, `type`, `fid`/`reunion` (selon), `modele`, `resultat` (succès/erreur + message), et pour un appel LLM : `tokens_in`, `tokens_out`, `duree_ms`, `cout_estime`, `version` produite.

Types d'opérations journalisés :

| Type | Exemple de contenu |
|---|---|
| `passe_complete` | périmètre (réunion/réunions), nb blocs, coût total, durée totale, statut (terminee/annulee/erreur) |
| `reformulation_bloc` | FID, version créée, type (`relance`, `relance_ciblee`), consigne, stats d'appel |
| `edition_manuelle` | FID, version `edition_manuelle` créée (stats null) |
| `validation` / `devalidation` | FID, version validée/dévalidée |
| `fusion_blocs` | FIDs sources, nouveau FID |
| `erreur_api` | appel concerné, fournisseur, message, après retry |
| `annulation_passe` | position d'arrêt, nb résultats conservés |
| `resume` / `synthese` | (P17) réunion, source, stats |

### 5.2 Règles

- **append-only** : jamais d'effacement ni de réécriture d'entrées ; fichier unique pour l'étude ;
- écriture à chaque opération (pas seulement en fin de passe) : le log survit à un crash ;
- le log ne fait foi pour rien : document d'audit et d'affichage uniquement, jamais consommé par le moteur ;
- l'affichage in-app (icône 📋 Log, spec UI §8) lit ce fichier en lecture seule.

## 6. Règles d'invariance (à tester unitairement)

1. Un appel LLM n'écrit jamais dans un document tant qu'il n'a pas abouti : aucun résultat partiel n'est stocké.
2. Une annulation à mi-passe ne détruit aucun résultat déjà versionné.
3. La troncation de contexte ne retire jamais la synthèse d'étude ni l'unité courante, et retire toujours les blocs les plus anciens de la fenêtre en premier.
4. Toute opération (passe, relance, édition, validation, fusion, erreur, annulation) produit exactement une entrée de log, horodatée, avant retour à l'UI.
5. La température effective d'un appel est : surcharge étude si définie, sinon réglage app ; jamais une valeur codée en dur dans le moteur.
6. Relancer une passe ne retraite jamais un bloc déjà traité sans demande explicite de l'utilisateur.
