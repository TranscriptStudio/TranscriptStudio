# Correctifs page Étude & synthèse d'étude (relecture David du 2026-11-09) — P18.9 + P20.6

Feuille d'autorité pour les points traités : **prime sur NAVIGATION_V2.md et NAVIGATION_MODIFS_V2.md** (page Étude), **amende P17.2 de la feuille de route** (génération automatique de la synthèse abrogée) et **complète P20.3** (emplacement des récurrences, détection des pensées redondantes).

## 1. Contexte et arbitrages

Relecture David du 09/11 au soir (capture de la page Étude, 9 points de relecture) après recette P14 → P19. Décisions actées le même jour :

1. **Clic gauche sur le corps d'une tuile de réunion** : sert uniquement au glisser-déposer (réordonnancement) ; il ne déclenche aucune navigation ni ouverture. La navigation vers une étape se fait par le clic sur le stepper de la tuile ou par le menu contextuel du clic droit.
2. **Injection de contexte conservée** : la synthèse d'étude, au nouveau format (phrases courtes par pensée), reste injectable comme contexte dans la reformulation des blocs cochés (rôle P17.2 conservé).
3. **Ré-alimentation d'une réunion déjà intégrée** : remplace exactement sa contribution, avec avertissement préalable (jamais de doublon, jamais de régénération implicite du reste).
4. **Détection des pensées redondantes dans l'ouvrage** : présélection locale sans LLM, confirmation par passe LLM à la demande sur la seule liste candidate.

## 2. P18.9 — Correctifs page Étude (décisions David du 09/11)

- **P18.9a Tuiles de réunion :** réordonnancement par **glisser-déposer** (montée/descente au pointeur) ; les **flèches de réordonnancement sont supprimées** (trop petites, peu ergonomiques) ; le **bouton « Ouvrir » est supprimé** (amende la série 4 de NAVIGATION_MODIFS_V2 — décision David prime). Le clic gauche sur le corps de la tuile ne fait rien d'autre que le déplacement. Une tuile de réunion non transcrite reste déposable normalement (mention discrète inchangée). **Navigation par tuile :** le **clic gauche sur une pastille du stepper** de la tuile ouvre la page Réunion directement à l'étape visée (comportement inchangé) ; le **clic droit sur la tuile** ouvre un menu contextuel regroupant : accès aux étapes (idem clic stepper), **« Retirer la réunion »**, **« Relocaliser »** (ces deux boutons disparaissent de la tuile ; « Relocaliser » garde son rôle de résolution du dossier réunion déplacé).
- **P18.9b Hauteur de tuile :** la suppression du bouton « Ouvrir » et des flèches libère une ligne par tuile ; l'**effet de rehaussement au survol** ne doit pas être rogné sur la première tuile en haut du conteneur (marge intérieure/clipping à corriger).
- **P18.9c Badge Bible simplifié :** la **versification n'est plus affichée comme un champ distinct** — elle découle de la version retenue (BIBLE_JND_V2 : défaut `darbyR` — Darby révisée). Badge : « Bible : Darby révisée ». L'**info-bulle du badge est épurée** : suppression des commentaires internes (notamment la référence à P18.5) ; libellé simple, sans texte de spec. Le traitement interne des écarts de versification (BIBLE_JND_V2 §4) est inchangé.
- **P18.9d Accès à l'ouvrage :** le bouton d'accès à la page Ouvrage est déplacé **en haut de page, à droite de « Ajouter une réunion »**, et libellé **« Édition ouvrage final »** ; les **boutons liés à la synthèse** (P20.6) sont placés à côté de lui.
- **P18.9e Fonds de page :** le bandeau supérieur et les labels présents sur la page retrouvent **exactement la teinte du fond de la page** (reliquat de la série 5 du hub) ; le correctif s'applique à toutes les pages présentant le reliquat.
- **P18.9f Défilement :** le conteneur des tuiles de réunion **défile indépendamment** — une étude complète peut compter plusieurs dizaines de réunions (recette : 30+).

Périmètre : page Étude uniquement. Le hub (dernières réunions) et la page Réunion sont inchangés sur ces points.

## 3. P20.6 — Synthèse d'étude repensée (décisions David du 09/11)

**Abrogation** : la génération automatique de la synthèse **à la validation d'une réunion** (P17.2) est abrogée — l'alimentation est **strictement manuelle**.

- **P20.6a Prompt dédié éditable :** la synthèse d'étude dispose de son propre prompt dans la bibliothèque éditable des réglages de l'app (`prompts/synthese_etude.md`, cf. UI_GESTION_PROMPTS_V2 : réinitialisation aux défauts embarqués, import/export, mode étude = copie locale). **Format cible : phrases courtes résumant chaque pensée émise par un interlocuteur** — plusieurs pensées par bloc possibles, phrases non nécessairement complètes — avec le locuteur identifiable. La synthèse sert d'aide à la rédaction de l'ouvrage : identifier les pensées redondantes d'un bloc à l'autre.
- **P20.6b Alimentation incrémentale manuelle :** clic droit sur la tuile d'une réunion **dont les blocs sont validés** → « **Alimenter la synthèse globale** » ; la contribution de la réunion est **ajoutée** à la synthèse existante (jamais de re-génération implicite du reste). Un bouton dédié en haut de page (à côté de « Édition ouvrage final », P18.9e) peut offrir le même accès. Ré-alimenter une réunion déjà intégrée **remplace exactement sa contribution**, avec avertissement.
- **P20.6c Mémoire des contributions :** la synthèse (niveau étude, cf. CONTRAT_STOCKAGE_REUNIONS_V2) mémorise la liste des réunions ayant contribué et l'empreinte des blocs validés pris en compte — pour l'idempotence, le remplacement ciblé (P20.6b) et l'avertissement « blocs re-validés depuis la dernière alimentation ».
- **P20.6d Régénération complète :** le bouton « **(Re)générer** » affiche un **avertissement explicite** avant toute action : si une synthèse est déjà présente, elle sera **entièrement remplacée** par la synthèse de toutes les réunions dont les blocs sont validés ; confirmation requise.
- **P20.6e Édition manuelle :** la zone d'édition de la synthèse est conservée (saisie manuelle possible) ; un bouton « **Annuler l'édition** » apparaît à côté de la sauvegarde, **en mode édition uniquement**, et restaure le texte antérieur.
- **P20.6f Injection de contexte conservée (arbitrage David) :** la synthèse au nouveau format reste **injectable comme contexte dans la reformulation des blocs cochés** (rôle P17.2 conservé) ; budget de contexte inchangé (fenêtre glissante, troncation par le haut — SPEC_MOTEUR_P15_V2 inchangé).
- **P20.6g Détection des pensées redondantes (page Ouvrage) :** nouvelle aide à la relecture qui s'appuie sur la synthèse : **présélection locale sans LLM** (comparaison normalisée des phrases courtes entre elles), puis **confirmation par passe LLM à la demande sur la seule liste candidate** (coût minuscule). Résultat : **liste de groupes de pensées redondantes avec liens cliquables vers les paragraphes correspondants de l'ouvrage** (via la provenance des paragraphes, P19.1). **Signalement uniquement, jamais de réécriture** — rejoint P19.4 (fusion de pensées) et l'outillage P20.3.

## 4. Amendement P20.3 — emplacement unique des récurrences

L'outillage « récurrences » (P17.3, affiché page Étude par P18.6c) **vit exclusivement dans la page Ouvrage** : liste des récurrences avec **liens permettant de les retrouver dans l'ouvrage** (vue dédiée P20.3 avec filtres, occurrences cliquables). **La page Étude n'affiche plus les récurrences.** P17.3/P18.6c sont abrogés sur ce seul point ; le mécanisme de détection (local sans LLM, passe LLM optionnelle sur les familles candidates) est inchangé et relevé par P20.3.

## 5. Règles d'invariance (à tester unitairement)

P18.9 :
1. Le clic gauche sur le corps d'une tuile de réunion ne déclenche aucune navigation ni ouverture ; seul le glisser-déposer modifie l'ordre ; l'ordre persiste (etude.json).
2. La page Étude n'affiche ni flèche de réordonnancement ni bouton « Ouvrir ».
3. Le clic droit sur une tuile n'ouvre que le menu contextuel (étapes, « Retirer la réunion », « Relocaliser »).
4. Le badge Bible n'affiche qu'une version, jamais de champ « versification » distinct ; l'info-bulle ne contient aucun commentaire de spec (aucune mention P18.5).
5. Le bouton d'accès à l'ouvrage est libellé « Édition ouvrage final » et placé à droite de « Ajouter une réunion » ; les boutons de synthèse sont à côté de lui.
6. Bandeau supérieur et labels de la page : teinte identique au fond de la page, sur toutes les pages concernées par le reliquat.
7. Le conteneur des tuiles de réunion défile indépendamment ; l'effet de rehaussement au survol est visible intégralement, y compris pour la première tuile.

P20.6 :
8. Aucune écriture automatique de la synthèse d'étude à la validation d'une réunion.
9. « Alimenter la synthèse globale » n'est proposé que pour une réunion à blocs validés ; l'opération n'altère pas les contributions des autres réunions.
10. Ré-alimenter une réunion déjà intégrée remplace exactement sa contribution (aucun doublon), après avertissement confirmé.
11. « (Re)générer » exige une confirmation après affichage de l'avertissement de remplacement intégral.
12. « Annuler l'édition » n'est visible qu'en mode édition et restaure le texte antérieur à l'édition.
13. La détection des pensées redondantes ne modifie jamais l'ouvrage ni la synthèse : signalement et liens uniquement ; la présélection locale n'entraîne aucun coût LLM.
14. La synthèse d'étude reste injectable comme contexte dans la reformulation des blocs cochés (format nouveau, mécanisme P15 inchangé).

## 6. Critères de recette

- Capture page Étude conforme aux points 2 (tuiles, clic droit, pas de bouton « Ouvrir »/flèches), 5 (« Édition ouvrage final » en haut), 6 (fonds), 7 (rehaussement première tuile), 8 (scroll) de la relecture.
- Étude de 30+ réunions : défilement fluide, réordonnancement par glisser-déposer persistant après réouverture.
- Badge « Bible : Darby révisée » sans champ versification ; info-bulle épurée.
- Synthèse sur l'étude de recette Luc : alimentation manuelle réunion 1 puis réunion 2 (ajout), ré-alimentation d'une réunion (remplacement avec avertissement), « (Re)générer » (avertissement de remplacement intégral), édition puis « Annuler l'édition », injection de contexte vérifiée sur un bloc coché.
- Détection des pensées redondantes sur l'ouvrage de recette : groupes proposés, liens navigables vers les paragraphes ; aucun coût LLM pour la présélection.
- Suite de tests verte ; aucune régression P18.7/P18.8/P19.

## 7. Série 2 — relecture 2 du 10/11 (P18.9-bis + conformité P20.6b) — PRIME sur la série 1 pour les points traités

Recette P18.9 par David le 10/11 (3 captures). Décisions actées :

- **P18.9-bis.a Numérotation positionnelle des réunions** : le glisser-déposer réordonne les tuiles mais le numéro de tuile ne se réactualise pas (« Réunion 2 » reste 2). Correction retenue : **le numéro disparaît de la tuile** ; une **gouttière à gauche des tuiles affiche des labels numérotés strictement positionnels** — le label 1 est toujours en haut, le label 2 sous lui, etc. ; **les labels ne bougent jamais : c'est la tuile qui change de rangée** au glisser-déposer (la numérotation reflète la position, jamais une identité). **Aucun label sans tuile** : N réunions affichées = labels 1 à N, rien au-delà. Le titre d'affichage de la réunion reste éditable (P18.8a, et P18.9-bis.f depuis la page Étude) ; l'ordre persiste dans etude.json (inchangé).
- **P18.9-bis.b Info-bulle de la zone des tuiles supprimée** : l'aide « Glissez-déposez une tuile pour réordonner l'étude… ; clic droit… ; clic sur une pastille… » au survol de la zone des tuiles disparaît — **aucune info-bulle au survol de la zone ou des tuiles**.
- **P18.9-bis.c Aucune mention Bible sur la page Étude** : amende P18.8d/P18.9c et la règle d'affichage de P20.5 — la page Étude **n'affiche plus aucune version de Bible** (ni le badge d'en-tête « Bible : Darby révisée », ni la mention « Bible — Traduction J. N. Darby révisée » sous la synthèse). La version reste visible : paramètres de l'étude (P18.8c), sélecteur du volet Réunion (P20.5a), lecteur de Bible (P18.10), page Ouvrage (P20.5b).
- **P18.9-bis.d Fonctions haut droit = vrais boutons** : « ＋ Ajouter une réunion », « Édition ouvrage final », « (Re)générer la synthèse », « Éditer » deviennent de **vrais boutons** (style bouton, états survol/pressé, focus clavier) ; **suppression des « ... »** de « ＋ Ajouter une réunion » et « (Re)générer la synthèse ».
- **P18.9-bis.e Info-bulle « (Re)générer la synthèse » raccourcie** : libellé simple et court (remplacement intégral par la synthèse des réunions à blocs validés ; alimentation réunion par réunion via clic droit sur une tuile), **aucune référence à la spec** (plus de « P20.6 »).
- **NON-CONFORMITÉ P20.6b (bug, pas un changement de spec)** : le menu contextuel d'une tuile (Transcription / Reformulation / Résumé / Retirer la réunion / Relocaliser…) **n'offre pas « Alimenter la synthèse globale »** alors que la réunion a des blocs validés — violation de l'invariant 9. Correction : entrée présente dès qu'une réunion a des blocs validés (libellé exact « Alimenter la synthèse globale »), absente sinon (invariants 9-10 inchangés).
- **P18.9-bis.f « Renommer… » au clic droit (décision David du 10/11)** : le menu contextuel d'une tuile de réunion (page Étude) gagne une entrée « Renommer… » qui édite le **titre d'affichage** de la réunion — même sémantique et même persistance que P18.8a (titre_1 si rattachée à une étude, champ « titre » du tier si autonome), sans effet sur les noms de fichiers/dossiers ni sur les références de l'étude.

### Invariants additionnels (15-19)

15. La gouttière gauche affiche exactement N labels numérotés 1 à N pour N tuiles, chaque label aligné sur la rangée de sa tuile ; les labels sont fixes (seule la tuile se déplace au glisser-déposer) ; aucun label n'est affiché sans tuile ; le titre d'une tuile ne porte jamais de numéro.
16. Aucune info-bulle ne s'affiche au survol de la zone des tuiles ou des tuiles de la page Étude.
17. La page Étude n'affiche aucune version de Bible (ni badge d'en-tête, ni mention bas de page).
18. Les 4 actions haut droit sont de vrais boutons, et **aucune info-bulle de l'app ne mentionne de référence de spec** (numéro de phase, P18/P20, etc.) — généralise l'invariant 4.
19. « Renommer… » (clic droit, page Étude) modifie uniquement le titre d'affichage de la réunion : jamais les noms de fichiers ou de dossiers, ni les références de l'étude.

### Critères de recette (série 2)

- Réordonnancement de 2 réunions : la tuile déplacée prend la rangée visée, les labels 1 et 2 restent en place (le 1 en haut) ; seuls les labels 1 et 2 sont affichés ; persistance de l'ordre vérifiée à la réouverture.
- Clic droit → « Renommer… » : titre modifié, visible partout (tuile de la page Étude, ruban du volet Réunion), sans changement de nom de dossier/fichier ni des références.
- Survol de la zone des tuiles : rien ne s'affiche.
- Page Étude sans aucune mention Bible (en-tête et bas de page).
- 4 boutons réels ; libellés « ＋ Ajouter une réunion » et « (Re)générer la synthèse » sans « ... ».
- Info-bulle « (Re)générer la synthèse » courte, sans référence de spec.
- Clic droit sur une réunion à blocs validés : « Alimenter la synthèse globale » présent et fonctionnel (ajout incrémental, invariants 9-10) ; absent pour une réunion sans bloc validé.
- Suite de tests verte.

## 8. Série 3 — relecture 3 du 10/11 (P18.11 : allègement du dialogue « Paramètres de l'étude ») — PRIME sur les séries 1-2, P15.2 et P18.8b pour les points traités

Relecture 3 par David le 10/11 : capture annotée du dialogue « Paramètres de l'étude » (seuls les champs encadrés en rouge sont à conserver). Les blocs « paramètres du modèle » et « prompts » de ce dialogue étaient devenus inutiles — depuis P18.7, toute opération sur les traitements d'une réunion utilise les paramètres du tier (l'étude ne modifie jamais les conditions de travail de la réunion) — et les zones de prompt y étaient illisibles (petit texte monospace). Décisions actées (arbitrages David du 10/11) :

- **P18.11a Champs conservés (les encadrés rouges de la capture)** : bloc **Général** (titre de l'étude, thème) ; **options de contexte de la reformulation** (« Envoyer les reformulations précédentes en contexte (fenêtre glissante) » **avec son champ « Fenêtre glissante (tokens) » conservé à côté** — arbitrage David du 10/11 —, « Envoyer la synthèse d'étude en contexte ») ; **résumé** (longueur cible, source par défaut) ; **Bible de référence** (version retenue + avertissement de propagation vers les tiers, P18.8c, et interdits stylistiques). Ces champs gardent leur sémantique, leur portée et leur persistance actuelles.
- **P18.11b Champs retirés** : les zones « Prompt système », les menus « Modèle » et les champs « Température », dans tous les blocs — **le dialogue n'expose plus aucun paramètre LLM ni aucun prompt**.
- **P18.11c Abrogation de la surcharge d'étude** (arbitrage David du 10/11 : « réglages de l'app uniquement ») : il n'existe **plus de surcharge par étude des paramètres LLM ni des prompts**. Les opérations sur les traitements d'une réunion utilisent les paramètres du tier (§8 du contrat de stockage, inchangé) ; la **synthèse d'étude** utilise **exclusivement les réglages de l'app** : paramètres LLM globaux + prompt courant de la bibliothèque (`prompts/synthese_etude.md`, P20.6a — amende : lecture directe de la bibliothèque, **plus de copie locale d'étude pour le prompt de synthèse** ; la version de synthèse continue de mémoriser le texte et le hash utilisés, P20.6c).
- **P18.11d Stockage** : le fichier `parametres\parametres.json` de l'étude ne porte plus de volets LLM (modèle/température/prompt). Les volets éventuellement présents dans une étude existante sont **ignorés à la lecture et jamais réécrits** (inertes, élagués à la prochaine écriture) — **aucune migration dédiée**. Les champs conservés (P18.11a) restent stockés comme aujourd'hui.
- **P18.11e Mécanisme ⚙ Prompts inchangé** : UI_GESTION_PROMPTS_V2 (§3-4) reste tel quel — l'édition depuis les pages de traitement modifie la copie locale de la réunion (jamais la bibliothèque sans « Promulguer » explicite). La présente décision ne retire que l'exposition des prompts et paramètres LLM dans le dialogue « Paramètres de l'étude », et la surcharge d'étude associée.

### Invariants additionnels (20-22)

20. Le dialogue « Paramètres de l'étude » n'expose aucun paramètre LLM (modèle, température) ni aucun prompt.
21. Il n'existe aucune surcharge d'étude de paramètres LLM ni de prompt : la synthèse d'étude utilise exclusivement les paramètres LLM globaux de l'app et le prompt courant de la bibliothèque (`prompts/synthese_etude.md`) ; les opérations d'une réunion utilisent les paramètres du tier.
22. Les volets LLM éventuellement présents dans `parametres\parametres.json` d'une étude créée avant P18.11 sont ignorés et jamais réécrits ; les champs conservés gardent leur sémantique, leur portée et leur persistance actuelles.

### Critères de recette (série 3)

- Dialogue conforme à la capture annotée : uniquement les encadrés rouges (titre/thème, options de contexte + champ tokens, longueur cible, source par défaut, version Bible + propagation, interdits stylistiques) ; aucune zone prompt, aucun menu modèle, aucune température.
- Modifier le prompt de synthèse dans la bibliothèque des réglages change la génération suivante (aucune copie locale d'étude).
- Opérations de réunion inchangées (paramètres du tier) ; aucune régression P18.7/P18.8 ; suite de tests verte.
