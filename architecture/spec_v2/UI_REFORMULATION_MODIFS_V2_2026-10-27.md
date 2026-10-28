
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
