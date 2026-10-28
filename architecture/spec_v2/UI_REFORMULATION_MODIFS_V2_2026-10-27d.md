
# Spec UI — Page Reformulation : correctifs de relecture (v2.1)

Feuille de spec de **modification/correction** de la page Reformulation (P16), suite à la première relecture de David (2026-10-27, avec capture d'écran). **En cas de conflit avec UI_REFORMULATION_V2.md sur les points traités ici, le présent document prévaut.** Chaque point précise : le constat (comportement livré), le besoin (intention de David), la spécification attendue.

## 1. Défilement unique synchronisé, blocs alignés horizontalement

**Constat** : chaque bloc est rendu dans une cellule de hauteur propre avec une barre de défilement verticale interne (le CLI a créé des « tailles verticales de blocs uniques »).

**Besoin** : pas de scroll interne au bloc ; un seul défilement vertical général pour toute la table, synchronisé sur les deux colonnes ; les blocs doivent être alignés horizontalement.

**Spécification** :
1. **Aucune barre de défilement dans une cellule de bloc** (ni colonne brute, ni colonne reformulée, ni regroupement de blocs) ; les cellules s'étendent à la hauteur de leur contenu.
2. **Une seule barre de défilement verticale pour toute la table** (vue d'ensemble des blocs), pilotant les deux colonnes simultanément.
3. **Hauteur de ligne = hauteur max des deux cellules du bloc** (brut ↔ reformulé) : la ligne du tableau s'aligne sur la plus haute des deux, l'autre cellule se cale en haut ; jamais de bloc décalé verticalement par rapport à son vis-à-vis.
4. L'alignement horizontal brut ↔ reformulé se maintient au défilement, au redimensionnement des colonnes et pendant l'édition (la ligne s'agrandit au fil de la frappe).
5. La timeline (ancrée en bas) n'est jamais affectée par le défilement vertical (comme déjà spécifié).
6. Implémentation suggérée : QTableWidget / modèle de vue avec des lignes à hauteur variable (`resizeRowsToContents`, pas de hauteur fixe), ou vue custom ; à la discrétion du CLI, mais le comportement observable ci-dessus est exigé et testé (fumée offscreen : aucune `QScrollBar` dans les cellules ; deux blocs visibles à des hauteurs différentes s'alignent).

## 2. Colonne locuteurs : noms, pas un panneau de filtre

**Constat** : le panneau de gauche est une liste de locuteurs à cases à cocher (filtre), détachée des blocs.

**Besoin** : retrouver simplement le nom du locuteur correspondant à chaque bloc. La fonction filtre peut être conservée mais sera éventuellement déployée plus tard via un menu déroulant de la barre supérieure.

**Spécification** :
1. La colonne de gauche est **une colonne de la table, une cellule par ligne de bloc**, affichant le nom du locuteur du bloc (ou les noms, séparés par « / », pour un bloc fusionné multi-locuteurs) ; pas de case à cocher, pas de panneau latéral séparé.
2. La largeur de la colonne locuteurs est fixe et juste suffisante (redimensionnable par l'utilisateur, largeur mémorisée — cf. §5 pour la persistance).
3. **La fonction de filtrage par locuteur est retirée de l'UI** mais pas de l'architecture : si une API de filtrage existe (modèle de données), elle est conservée en l'état, prête à être rebranchée plus tard sur un menu déroulant « Filtrer par locuteur… » de la barre supérieure. **Ne pas implémenter ce menu maintenant.**
4. La pastille d'état et l'indicateur de version restent dans la cellule reformulée, comme déjà spécifié.

## 3. Largeur du panneau gauche de la timeline

**Constat** : la timeline en bas a un large canal/panneau gauche (zone des noms), bien plus large que la colonne locuteurs au-dessus.

**Spécification** :
1. La zone située à gauche de la timeline doit avoir **exactement la même largeur que la colonne locuteurs** située au-dessus, de sorte que le bord gauche de la timeline s'aligne sur le bord gauche des colonnes de texte (alignement vertical homogène de toute la page).
2. Les commandes de la timeline (masquage, zoom, curseur) restent inchangées par ailleurs.

## 4. Liaison correction de transcription → reformulation

**Constat** : depuis la fenêtre de correction de transcription (éditeur v1), il n'existe aucune route vers la reformulation.

**Spécification** :
1. Dans la fenêtre de correction de transcription (éditeur v1), ajouter un bouton **« Reformulation… »** qui ouvre la page de traitement Reformulation **de la réunion courante**.
2. Le bouton n'est actif que si le projet appartient à une étude (référencé comme réunion). Sinon : masqué, ou désactivé avec l'info-bulle « Ce projet n'appartient à aucune étude » (au choix du CLI, cohérent avec l'existant).
3. Cas limite : le projet appartient à plusieurs études → petit dialogue de choix de l'étude (liste), ou à défaut ouvrir l'étude la plus récente qui le référence ; à la discrétion du CLI, documenté dans PROJECT_STATE.md.
4. Ce bouton est la brique inverse du lien existant « Ouvrir dans l'éditeur » de la page Étude — même style de navigation (fenêtre/onglet selon l'architecture actuelle), retour possible vers la correction.

## 5. Persistance de la taille de police

**Constat** : la taille de texte réglée avec A+/A− revient toujours à la valeur standard à la réouverture ; et la police par défaut est trop grande pour une lecture en double colonne.

**Spécification** :
1. Le réglage A+/A− est **mémorisé dans les paramètres de l'app** (SettingsManager) et **réappliqué à chaque ouverture** de la page Reformulation (et de l'éditeur v1 s'ils partagent déjà ce contrôle) ; une étude rouverte retrouve la taille enregistrée.
2. **Le défaut est abaissé** pour convenir à la double colonne (lecture brut ↔ reformulé côte à côte sans retours à la ligne excessifs) ; valeur par défaut au choix du CLI, vérifiée en relecture par David.
3. La plage A+/A− reste bornée comme aujourd'hui ; le bouton et le raccourci restent inchangés.

## 6. Règles d'invariance additionnelles (à tester)

1. Aucune barre de défilement verticale n'est visible à l'intérieur d'une cellule de bloc, quel que soit le contenu (fumée : parcourir les widgets et l'arbre de la table).
2. À tout instant, pour chaque bloc visible, le haut de la cellule brute et le haut de la cellule reformulée sont sur la même ligne horizontale.
3. La largeur de la zone gauche de la timeline est égale à celle de la colonne locuteurs (à la tolérance de bordure près).
4. Après fermeture/réouverture de l'app, la taille de police configurée et la largeur des colonnes sont conservées.
5. « Reformulation… » depuis l'éditeur v1 aboutit toujours à la page Reformulation de la même réunion (jamais d'une autre), et n'est pas actif pour un projet hors étude.

## 7. Livraison

Correctifs à intégrer à la prochaine session CLI (phase P16-bis « correctifs de relecture UI ») ; chaque point ci-dessus est indépendant et testable séparément. Recette finale par David sur la réunion de test.

---

# 2ᵉ série de correctifs (2ᵉ relecture David, 2026-10-27 — capture image-4/image-5)

> Rappel : les correctifs de la 1ʳᵉ série (scroll unique synchronisé, colonne locuteurs = noms par bloc, largeur zone gauche timeline, liaison éditeur v1, persistance police) ne sont **pas encore appliqués à cette relecture** — la 2ᵉ série s'y ajoute pour la même passe de livraison P16-bis. Les nouveaux points ci-dessous précisent ou étendent les points déjà spécifiés quand ils les recoupent.

## 8. Synchronisation timeline ↔ blocs (2 points)

**Constat** : la timeline n'est pas synchronisée avec la table des blocs (capture image-4).

**Spécification (bidirectionnelle)** :
1. **Clic sur un bloc** (colonne brute, cellule locuteurs ou pastille) : le curseur audio se positionne au début du bloc et la timeline s'illumine/scrollle pour rendre le segment visible ;
2. **Clic sur la timeline** : le curseur se positionne et le bloc correspondant est sélectionné/défilé dans la table (le bloc contenant la position devient le bloc courant) ;
3. **Pendant la lecture** : le bloc contenant le curseur est visuellement surligné dans la table (cf. §9 pour la couleur) et la vue défile automatiquement pour le garder visible (défilement « paresseux » : seulement quand il sort de la zone visible ; jamais de défilement si l'utilisateur est en train de sélectionner/éditer) ;
4. positions = audio traité (contrat §6) ; la conversion vers l'original reste interne.

## 9. Couleurs du surlignage : contraste selon le thème

**Constat** : le surlignage jaune du texte (sélection dans le texte brut) est illisible en mode sombre.

**Spécification** :
1. Le surlignage (sélection de texte et surbrillance « bloc en cours de lecture », §8.3) utilise des **couleurs définies par thème** (clair et sombre), avec un texte qui reste lisible sur le fond surligné (contraste AA minimum) ;
2. test systématique de la page dans **les deux thèmes** (fumée offscreen + relecture David) ; aucune couleur codée en dur partagée entre les thèmes.

## 10. Largeur de la timeline : gouttière gauche et marge droite

**Constat** : la zone « locuteurs » à gauche de la timeline reste beaucoup trop large, et il subsiste un espace inutile à droite de la timeline.

**Spécification** (précise §3 de la 1ʳᵉ série) :
1. **Gouttière gauche** : exactement la largeur de la colonne locuteurs de la table (alignement vertical avec les colonnes au-dessus) ; si la timeline a besoin d'une zone de noms propre, les noms s'affichent dans cette largeur, sans colonne supplémentaire ;
2. **Bord droit** : les pistes de la timeline s'étendent **jusqu'au bord droit de la fenêtre** : aucune gouttière ni marge décorative à droite ; l'échelle de temps couvre toute la largeur restante ;
3. La hauteur de la timeline reste compacte (composant v1 ancré en bas, masquable).

## 11. Navigation : « Accueil » et pages multiples

**Constat** : le bouton « Accueil » de la page Reformulation ouvre la page Étude (capture image-5) ; en naviguant, plusieurs pages Étude peuvent s'empiler.

**Spécification — modèle de navigation unique** :
1. L'app possède **une seule fenêtre principale** avec des pages empilées en pile : **Accueil → Étude → Réunion (Correction / Reformulation)** ; « Accueil » ramène **toujours à la page d'accueil** de l'app (projets récents + études récentes), jamais à la page Étude ;
2. la page Étude est accessible depuis l'accueil (liste des études récentes, « Ouvrir une étude ») et depuis une page Réunion via un bouton **« Retour à l'étude »** distinct ;
3. **pas de pages dupliquées** : ouvrir une étude (ou une réunion) déjà affichée dans la pile **réactive la page existante** au lieu d'en empiler une nouvelle ; la pile ne contient jamais deux fois la même page (étude, correction, reformulation d'une même réunion) ;
4. l'empilement existant type « fenêtres séparées » pour l'éditeur v1 (P14.3) est remplacé par ce modèle à pile unique — à la discrétion du CLI si un point exige une fenêtre séparée (ex. comparaison côte à côte), documenté dans PROJECT_STATE.md.

## 12. Page d'accueil : « Ouvrir une étude depuis un dossier »

**Spécification** :
1. Dans la section Études de l'accueil, à côté de « Ouvrir une étude » (liste des études récentes), ajouter **« Ouvrir depuis un dossier… »** : sélection d'un dossier (QFileDialog), validation de la présence d'un `etude.json` (sinon message clair « Ce dossier n'est pas une étude »), ouverture ;
2. l'étude ainsi ouverte rejoint la liste des études récentes ;
3. même mécanique que « Ouvrir un projet » v1 pour la symétrie d'usage.

## 13. Terminologie : « réunion » partout (arbitré 2026-10-27)

David a validé le renommage UI : l'objet « un enregistrement transcrit » s'appelle **« réunion » partout dans l'interface**, dans toute l'app (v1 comme v2).

1. **Portée UI** : tous les libellés visibles — accueil (« Réunions récentes », « Nouvelle réunion », « Ouvrir une réunion »), éditeur, dialogues, messages, barres de titre, manuel utilisateur ; le mot « projet » disparaît de l'UI.
2. **Inchangé (vocabulaire technique interne)** : le format de fichier/dossier v1, le code (`project_io`, `load_project`…), les specs (« projet v1 » désigne l'objet technique), le registre du disque (dossiers de projets inchangés, aucune migration) ; il s'agit d'un renommage d'affichage uniquement.
3. Dans l'UI, le couple naturel est donc : **une étude** (l'ouvrage) contenant des **réunions** (les enregistrements) ; une réunion hors étude reste une réunion.
4. Revue systématique des textes utilisateurs (boutons, menus, messages d'erreur, aide) lors de la passe P16-bis ; i18n français comme d'habitude.

## 14. Règles d'invariance additionnelles (2ᵉ série)

1. Cliquer un bloc positionne toujours le curseur audio à son début ; cliquer la timeline sélectionne toujours le bloc contenant la position (aller-retour cohérent, test offscreen).
2. Pendant la lecture, le bloc courant est surligné et visible sans intervention de l'utilisateur.
3. Le surlignage de sélection et de lecture est lisible dans les deux thèmes (aucun jaune clair sur fond sombre).
4. La gouttière gauche de la timeline a la largeur de la colonne locuteurs ; aucune marge vide à droite des pistes.
5. « Accueil » ouvre toujours la page d'accueil ; il n'existe jamais deux pages de la même étude/réunion dans la pile.
6. « Ouvrir depuis un dossier… » refuse proprement un dossier sans `etude.json` et n'ouvre rien dans ce cas.

---

# 3ᵉ série de correctifs (3ᵉ relecture David, 2026-10-27 — captures image-6/image-7)

## 15. Lecteur audio : état au retour sur la page

**Constat** : la lecture fonctionnait ; David a quitté la page Reformulation vers la page Étude pendant la lecture ; au retour, plus de son (lecteur en état zombie).

**Spécification** :
1. **Quitter la page Reformulation** (vers Étude ou Accueil) **arrête proprement la lecture** et libère les ressources audio (pas de son orphelin en arrière-plan) ;
2. **revenir sur la page** réinitialise un lecteur sain et **jouable immédiatement** : le bouton lecture/pause fonctionne dès le retour (curseur conservé là où il était si possible, sinon à zéro — au choix du CLI, documenté) ;
3. en cas d'erreur du périphérique audio au retour (rare), message clair dans la barre d'état plutôt qu'un échec silencieux.

## 16. Aucune lecture automatique au clic

**Constat** : un clic ou double-clic dans la page peut lancer la lecture automatiquement.

**Spécification** :
1. **Seul le bouton lecture/pause lance la lecture** — dans toute la page Reformulation ;
2. le clic (simple ou double) sur un bloc, une cellule, la timeline ou la colonne locuteurs **positionne le curseur et sélectionne, sans jamais déclencher l'audio** ;
3. invariant testé : aucun chemin de clic ne met le lecteur en état « lecture » (fumée : cliquer partout, vérifier que le bouton reste en état « lecture » disponible/pause non lancée).

## 17. Clé API LLM : persistance et parité ElevenLabs

**Constat** : la clé API LLM semble devoir être renseignée à chaque fois ; l'UX diffère de celle d'ElevenLabs (affichage •••••• masqué + test fonctionnel sans ressaisir).

**Spécification** :
1. La clé est **persistée dans le CredentialStore v1** (comme ElevenLabs), une entrée par fournisseur (identifiant de fournisseur du catalogue, stable) ;
2. UX identique à ElevenLabs : une fois la clé enregistrée, le champ affiche des **•••••• masqués** ; le bouton « Tester la connexion » fonctionne **sans ressaisir la clé** ; vider le champ = effacer la clé (intention explicite) ;
3. diagnostiquer la régression (cause probable : clé stockée sous un identifiant de fournisseur non stable, ou non sauvegardée du tout à la fermeture des réglages) et corriger à la racine — la clé doit survivre à un redémarrage complet de l'app ;
4. invariant : saisir la clé, quitter l'app, la rouvrir → « Tester la connexion » réussit sans ressaisie.

## 18. Éditeur de catalogue : listes de modèles par fournisseur

**Constat** (captures image-6/image-7) : doublons dans la liste (« gpt-6-astra » ×4 chez OpenAI), modèle d'un fournisseur affiché chez un autre (gpt-6-astra sous Mistral AI), identifiant et nom affiché incohérents (« gpt-6-astra » affichant l'identifiant `mistral-large-latest`), Base URL vide, prix 0,000 et « Contexte inconnu » pour des modèles connus du catalogue par défaut.

**Spécification — l'éditeur est strictement lié à la sélection** :
1. **Chaque fournisseur n'affiche que SES modèles** : la liste « Modèles » reflète exclusivement les modèles du fournisseur sélectionné à gauche ; changer de fournisseur recharge la liste et **désélectionne tout modèle** (panneau de droite vide/état par défaut tant qu'aucun modèle de CE fournisseur n'est sélectionné) ;
2. le panneau d'édition d'un modèle reflète **le modèle sélectionné dans la liste du fournisseur courant** — jamais un modèle d'un autre fournisseur ni un index orphelin (c'est la cause probable des incohérences constatées : index de sélection réinterprété dans une autre liste) ;
3. **pas de doublons** : un identifiant de modèle est unique au sein d'un fournisseur (l'ajout d'un doublon est refusé avec message) ;
4. les fournisseurs du **catalogue par défaut** arrivent **préremplis** : Base URL, prix entrée/sortie, température supportée, contexte maximal (les valeurs du catalogue embarqué) ; « Réinitialiser les valeurs par défaut » restaure l'état embarqué ;
5. ajout/suppression d'un modèle modifie la liste du fournisseur courant uniquement ;
6. invariants testés : (a) sélectionner successivement chaque fournisseur affiche uniquement ses modèles ; (b) le panneau de droite affiche toujours le modèle sélectionné dans la liste de gauche du même fournisseur ; (c) aucune liste ne contient de doublon ; (d) un fournisseur par défaut non modifié conserve Base URL, prix et contexte non vides.