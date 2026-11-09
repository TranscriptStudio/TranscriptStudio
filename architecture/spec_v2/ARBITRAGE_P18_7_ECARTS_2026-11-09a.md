# Arbitrage atelier — écarts de la livraison P18.7 (2026-11-09a)

Contexte : P18.7 livré le 08/11 (697 tests verts, commits a962a5f, 6e1aa46, a33eb0a, 4ad6577, e734f10) sur le cahier des charges du message ; le contrat CONTRAT_STOCKAGE_REUNIONS_V2_2026-11-09a.md est publié par la présente synchro. L'atelier a rapproché la livraison du contrat publié.

## Conformité : ACTÉE

Livraison conforme au contrat, point par point : structure du tier (§2), FID à portée réunion et identité (réunion, FID) (§4), schémas reformulation/résumé inchangés (§6), journaux par périmètre (§7), paramètres du tier et surcharges synthèse seule (§8), aucune écriture en retour testée à l'octet (§8bis, P18.7b/c et P18.7e), rattachement non destructif et divergences signalées jamais auto-corrigées (§10), migration one-shot avec sauvegarde, éclatement, requalification des références (provenances ouvrage y compris instantanés de fusion et historique), contrôle d'intégrité avant suppression, idempotence et reprise (§11), invariants §12 testés, non-régression P19 vérifiée (génération, fusion, dé-fusion identiques après migration).

## Écarts soumis par le CLI — décisions de l'atelier

**Écart 1 — Contrat non publié à la session.** Résolu par la présente synchro (contrat + feuille de route + index ci-joints). La livraison est requalifiée « conforme au contrat publié ».

**Écart 2 — Dialogues de paramètres de la page Étude propageant vers les tiers : VALIDÉ, avec une exigence d'explicité.** La propagation à l'enregistrement est une commande explicite de l'utilisateur, pas une écriture « en retour » au sens du §8bis (aucun effet caché). Exigence : le dialogue doit afficher clairement que l'enregistrement s'applique aux N réunions rattachées (libellé explicite, jamais silencieux) ; l'édition par réunion reste possible depuis la page Réunion (paramètres du tier). À couvrir par un test UI du libellé.

**Écart 3 — Badge « Bible » de la page Étude : VALIDÉ en version « commune + mixte ».** Le badge affiche la version commune aux tiers des réunions rattachées ; si les versions divergent entre réunions, il affiche « Bibles mixtes » avec info-bulle listant les versions par réunion. Le sélecteur de version prévu en P18.8c (paramètres de l'étude) propage la version choisie vers tous les tiers à l'enregistrement (même mécanique que l'écart 2), avec l'avertissement de versification inchangé (écart = information, jamais de ré-alignement automatique — BIBLE_JND_V2).

**Écart 4 — Invariant 1 reformulé : ACCEPTÉ tel quel.** Ouvrir une étude ne modifie jamais un projet v1 ; l'attachement peut créer le sous-dossier additif transcriptstudio\ (et y inscrire etudes[]) ; la première opération de traitement matérialise le tier. Conforme à l'esprit du contrat (additif, namespacé). Le contrat publié (invariant 1 du §12) couvre déjà ce cas (« hors du sous-dossier additif transcriptstudio\ »).

**Écart 5 — Couche de compatibilité FID nu en lecture : ACCEPTÉE en transitoire.** Le couple (réunion, FID) est l'identité canonique partout dans le stockage et les références ; les signatures historiques (FID nu) restent tolérées en lecture tant que non ambiguës. À supprimer en P20 (v2.1) lors du grand ménage : le retrait doit être un point explicite des critères P20.

## Suite

P18.8 (correctifs de relecture David du 08/11) est la prochaine phase ; l'écart 3 ci-dessus en précise le point (c) pour le badge Bible. Puis recette humaine P16/P17/P18/P18.6/P18.7/P19 (checklist PROJECT_STATE), puis P20.
