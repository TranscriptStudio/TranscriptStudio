# Spécification — Refonte de la navigation : hub, Réunion, Étude, Ouvrage (P18.6)

Statut : **fait autorité** pour la phase P18.6 (décisions validées par David, maquettes HTML du 2026-10-29). Elle **complète** les specs existantes (contrat format étude, moteur P15, UI Reformulation P16/P16-bis, P17, P18.5) ; en cas de conflit avec UI_REFORMULATION_V2.md / UI_REFORMULATION_MODIFS_V2.md sur les seuls points de navigation traités ici, le présent document prévaut. Les maquettes validées (hub, Réunion, Étude, Ouvrage) sont les références visuelles.

## 1. Modèle de navigation — 4 pages

L'app comporte quatre pages de premier rang : **Accueil (hub)**, **Réunion**, **Étude**, **Ouvrage**.

1. La navigation à pile unique (P16-bis, AppWindow) est conservée ; chaque page interne offre un bouton **Accueil**.
2. Le **bandeau app** (logo, sous-titre, version, pastilles de services, ⚙, ?) n'apparaît **que sur l'accueil** — jamais répété sur les autres pages.
3. Boutons **persistants** sur toutes les pages internes : **Accueil**, **⚙ Paramètres**, **? Aide** ; plus **« Gestion de l'étude »** sur les pages Réunion et Ouvrage, et **« Modifier l'étude »** sur la page Étude.

## 2. Page Accueil (hub)

1. **Trois tuiles** (libellés exacts) : « Nouvelle transcription » / « Reprendre une réunion » / « Études ». Une étude est un regroupement de réunions ayant pour objet un thème spécifique.
2. Bandeau : logo (l'app utilise \`icons/logo.png\`), sous-titre, version ; pastilles « Transcription ElevenLabs » et « Service IA » — verte si clé API configurée, grise sinon, info-bulle au survol ; FFmpeg et Bible n'y figurent pas (diagnostic uniquement pour FFmpeg ; la version de Bible est propre à chaque étude, affichée dans son contexte) ; boutons ⚙ et ?.
3. Salutation « Bonjour », sans prénom.
4. **Dernières réunions** : liste en une colonne ; chaque mini-tuile affiche le titre, l'étude (ou « Réunion autonome » + lien « rattacher à une étude… »), le stepper complet ①→⑥ et le coût. Le ⑥ Export **est conservé ici** : il peut y avoir des réunions autonomes et il est utile de savoir qu'un document a été exporté.

## 3. Page Réunion

1. **Ruban** : titre de la réunion (configurable, §6.4), date · durée ; badge « Étude \"…\" · Bible : [version retenue] » ou « Réunion autonome » ; boutons Gestion de l'étude, Accueil, ⚙, ?.
2. **Stepper fixe en haut** : ① Prétraitement · ② Transcription · ③ Correction · ④ Reformulation · ⑤ Résumé · ⑥ Export ; couleurs gris (à faire) / bleu (en cours) / vert (terminé).
3. **④ Reformulation et ⑤ Résumé sont optionnelles** (contour pointillé) : le bouton « Étape suivante » précise « (optionnelle) » le cas échéant, « passer l'étape › » permet de les sauter ; le passage direct ② Transcription → ⑥ Export est toujours possible. L'étape ⑤ Résumé est conservée : David lit le résumé de la réunion précédente en début de réunion suivante.
4. ⑥ Export reste sur cette page : **export de réunion** (y compris autonome ou intermédiaire — cf. §8).
5. Le contenu de la page selon l'étape courante reprend les specs existantes (P16/P16-bis/P17) sans changement.

## 4. Page Étude

1. **Ruban** : titre de l'étude, thème, nombre de réunions ; badge « Bible : [version] · versification : [nom] » (versification = information consultable, cf. P18.5) ; boutons Modifier l'étude (mini-fenêtre titre + thème, extensible), Accueil, ⚙, ?.
2. **Liste des réunions en une colonne** (même langage que le hub) : titre, rang, date, durée ; stepper d'avancement **①→⑤ sans ⑥** (l'objectif final étant l'export global de l'ouvrage, l'état d'avancement d'une étude n'affiche pas l'export) ; bouton « Ouvrir » ; coût par réunion ; poignée de **réordonnancement** (l'ordre vaut ordre d'ouvrage).
3. **« ＋ Ajouter une réunion »** : nouvel audio, ou reprise d'une réunion autonome (rattachement, §6).
4. Synthèse d'étude et récurrences (P17) affichées ; « régénérer » / « éditer ».
5. L'**export ouvrage** renvoie vers la **page Ouvrage** (l'assemblage et l'export final s'y font).

## 5. Page Ouvrage (précisions sur P19/P20)

La mécanique (modèle de données, régénération, fusion de pensées, mobilité, export structuré) reste définie par P19/P20 de la feuille de route ; la maquette validée précise la **présentation** :

1. **Trois zones** : arborescence à gauche, document compilé éditable au centre, rapport d'analyse à droite.
2. **Arborescence à la Word, largeur réglable** : les titres (chapitres) sont ajoutés **manuellement** — l'enchaînement des réunions ne suit pas les chapitres ; les sous-titres thématiques (granularité plus fine que le chapitre) sont ajoutés manuellement ou sur **suggestion IA** (jamais insérés automatiquement) ; chaque section indique la réunion source (R1, R2, …) ; les réunions non placées restent visibles en **« Réserves »**.
3. **« Analyser la cohérence » à la demande** : répétitions, incohérences, sujets récurrents (×n) ; chaque alerte est cliquable et navigue au passage concerné ; rien n'est modifié sans validation explicite.
4. **« Re-vérifier les versets bibliques »** : bouton dédié, redondance assumée avec le contrôle qualité fait à la reformulation (premier recours = reformulation ; re-vérification ici = aisance, jamais d'automatisme).
5. **Export final** depuis cette page (DOCX ; TXT/Markdown si déjà livrés en P18.3).

## 6. La réunion : objet de premier rang

1. Une réunion existe **indépendamment de toute étude** (réunion autonome) ou appartient à **exactement une étude** (exclusivité — inversion de l'invariant 13.5 du contrat, cf. ARBITRAGE_EXCLUSIVITE_REUNIONS).
2. « Rattacher à une étude… » est disponible **à tout moment, dès le prétraitement**.
3. **Changement d'étude** : confirmation demandée ; **les traitements déjà réalisés restent à l'ancienne étude** (option A, arbitrée) — la réunion est déliée puis rattachée, sans déplacement ni copie des résultats.
4. **Titre de réunion configurable à la création** ; défaut = nom du fichier audio.

## 7. Saisie manuelle (sans IA)

1. Tout bloc reformulé et tout résumé est **saisissable ou éditable directement** (copier-coller), sans aucun appel LLM.
2. Un contenu **validé (saisie manuelle)** a exactement le même statut qu'un contenu validé après traitement IA : il entre dans la compilation de l'ouvrage au même titre.
3. Toute saisie manuelle est tracée dans le log des opérations (§11 du contrat, type « édition manuelle »).

## 8. Exports — trois portées

1. **Réunion** (page Réunion, étape ⑥) : y compris autonome ou intermédiaire.
2. **Ouvrage / étude** : assemblage et export final depuis la **page Ouvrage** ; la page Étude y renvoie.
3. **Résumé** : selon P17.

## 9. Règles d'invariance (à tester unitairement)

1. Une réunion appartient à **0 ou 1** étude, à tout instant.
2. Le bandeau app n'apparaît que sur la page Accueil.
3. Les étapes ④⑤ restent optionnelles : le passage direct ②→⑥ est toujours possible et n'invalide jamais les contenus existants.
4. L'affichage d'avancement de la page Étude ne montre jamais l'étape ⑥.
5. Un changement d'étude ne déplace ni ne copie aucun traitement : tout reste à l'ancienne étude, la réunion change seulement de rattachement.
6. Une saisie manuelle validée est équivalente à un résultat IA validé (statut, compilation, invariants) — aucune discrimination de provenance dans l'ouvrage final.
7. Les suggestions IA (sous-titres, analyse de cohérence) ne sont jamais insérées ni appliquées sans validation explicite de l'utilisateur.
8. La pile de navigation ne contient jamais deux fois la même page (retour Accueil toujours disponible en un clic).

## 10. Livraison

Phase **P18.6**, avant P19/P20. Code additif, aucune régression P16/P16-bis/P17/P18/P18.5 ; navigation à pile unique conservée ; tests unitaires des invariants §9 ; manuel utilisateur mis à jour (navigation 4 pages, rattachement, saisie manuelle).