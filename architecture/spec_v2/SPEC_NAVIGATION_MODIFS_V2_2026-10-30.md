# Spec — Refonte navigation : correctifs de relecture (P18.6-bis)

Feuille de correctifs suite à la première relecture de David (captures du 2026-10-30, après livraison P18.6 par le CLI). **En cas de conflit avec SPEC_NAVIGATION_V2 ou toute autre spec UI sur les points traités ici, le présent document prévaut.** Les maquettes HTML validées (hub, Réunion, Étude, Ouvrage) restent les références visuelles. Chaque point : constat / attendu.

## Page Accueil (page de garde)

1. **Les trois entrées sont de petits boutons sans description.** Attendu : trois **grandes tuiles** côte à côte, chacune avec icône, titre exact et paragraphe descriptif :
   - « Nouvelle transcription » — « Prétraiter un audio (optionnel), lancer la transcription et éventuellement poursuivre le processus (reformulation, etc.). »
   - « Reprendre une réunion » — « Reprendre le travail où vous l'avez laissé : correction de transcription, reformulation, résumé, etc. »
   - « Études » — « Créer une étude, ouvrir et gérer une étude existante. Une étude est un regroupement de réunions ayant pour objet un thème spécifique. »
   Le clic sur la tuile déclenche l'action. Icônes : fournies en dur par David (à intégrer quand disponibles) ; placeholder sobre en attendant.
2. **Sous-titre du bandeau** : « Prétraitement audio et transcription assistée par ElevenLabs » → **« Prétraitement audio, transcription et reformulation assistés »**.
3. **Version affichée** : « Version 1.0 — Octobre 2026 » → **« Version 2.0 »** (sans date).
4. **Section « Études » en bas du hub** (liste + barre « Nouvelle étude / Ouvrir depuis un dossier… / Ouvrir l'étude sélectionnée ») : **à retirer du hub**. La tuile « Études » ouvre une **vue dédiée** des études (liste, « Nouvelle étude », « Ouvrir depuis un dossier… »). Le hub reste épuré : bandeau, salutation « Bonjour », 3 tuiles, dernières réunions.
5. **Dernières réunions** : structure conforme (stepper complet ①→⑥ conservé, coût, bouton Ouvrir). Le titre affiché est le **titre de la réunion** ; son renommage reste possible (à la création et a posteriori — défaut : nom du fichier audio).

## Page Réunion

6. **Bandeau app complet (grand logo + description) affiché en haut de la page** : interdit hors accueil (invariant §9.2 de SPEC_NAVIGATION_V2). À supprimer — le ruban réunion ouvre la page.
7. **Double navigation** : rangée d'onglets (Prétraitement…Export) **et** stepper. **Supprimer les onglets** ; le stepper seul pilote les étapes (SPEC_NAVIGATION_V2 §3.2).
8. **Bouton « Retour à l'étude » dans la barre d'outils** : supprimer — remplacé par « Gestion de l'étude » du ruban (décision du 2026-10-28).
9. **Badge d'étude** : « Bible : Bible - Traduction J. N. Darby révisée » → « Étude « Évangile selon Luc » · Bible : Darby révisée » — nom court de version, pas de doublon « Bible : Bible ».
10. **Couleurs du stepper** : uniformes partout — gris = à faire, **bleu = en cours**, vert = terminé ; ④⑤ en contour pointillé (conforme sur la page Étude, à généraliser).

## Page Étude

11. **Badge Bible trop technique** : « Bible : Bible — Traduction J. N. Darby révisée · vérification : Édition 2026 (rév. 2.3) » → **« Bible : Darby révisée · versification : Darby »** (les détails d'édition restent consultables, jamais affichés dans le ruban).
12. **Date des tuiles** : afficher la **date de la réunion** (date de l'audio), pas une date technique (rattachement).
13. **Titre des tuiles** : pas de numérotation (« 1. ») ni de nom de fichier brut — titre de réunion lisible ; le rang (réunion 1, 2, …) est une information annexe à côté du titre (cf. maquette).
14. **Boutons par tuile** (« Reformulation… », « Résumé… », ⚙) : supprimer — le clic sur la tuile ou « Ouvrir » ouvre la page Réunion. Seuls « Ouvrir » et le coût restent.
15. **Formulation** : « 2 réunion(s) » → « 2 réunions » (et partout : pluriels propres).
16. **« ＋ Ajouter une réunion »** : conforme ; à placer en tête de liste, à côté du titre de section « Réunions de l'étude » (cf. maquette).

## Page Ouvrage

17. Version intermédiaire acceptable en attendant P19/P20 : conserver l'aperçu d'assemblage et « Exporter l'ouvrage… » ; la page complète (arborescence, document, rapport d'analyse) arrive en P19/P20. Le renvoi depuis la page Étude doit rester visible.

## Invariants complémentaires (à tester unitairement)

1. Le hub n'affiche jamais la liste des études (vue dédiée via la tuile).
2. Aucun bandeau app hors accueil ; aucune rangée d'onglets sur la page Réunion.
3. Les libellés de versions bibliques utilisent le nom court : darby = « Darby », darbyR = « Darby révisée », segond1910 = « Segond 1910 ».
4. Les dates affichées pour une réunion sont toujours des dates de réunion (audio), jamais des dates techniques.

## Livraison

Phase **P18.6-bis**, correctifs uniquement, aucune régression sur ce qui est conforme (⠿ réordonnancement, Ajouter une réunion, ④⑤ pointillées, absence du ⑥ sur la page Étude, pastilles de services, boutons Accueil/⚙/?/Gestion de l'étude). Capture par capture, conformité aux maquettes validées.