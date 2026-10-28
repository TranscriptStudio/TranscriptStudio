
# Spécification UI — Page Reformulation (v2 — P16)

Ce document définit l'interface de la page de traitement Reformulation. Il complète le contrat du format étude (les données manipulées y sont définies) et fait autorité pour l'implémentation de P16.

> ⚠️ **Correctifs de relecture (2026-10-27)** : la feuille « Spec UI Reformulation : correctifs de relecture (v2.1) » (asset `spec/UI_REFORMULATION_MODIFS_V2.md`) prévaut sur le présent document pour les points qu'elle traite : défilement unique synchronisé (pas de scroll interne au bloc), colonne locuteurs = noms par bloc (filtre retiré de l'UI, réactivable plus tard via menu de la barre supérieure), largeur de la zone gauche de la timeline alignée sur la colonne locuteurs, liaison éditeur v1 → Reformulation, persistance de la taille de police.

## 1. Principe directeur

La page est une **table de relecture en lecture parallèle** : chaque bloc de parole apparaît sur une ligne unique dont la moitié gauche montre le texte brut corrigé (référence, avec audio) et la moitié droite le texte reformulé (éditable). L'alignement horizontal permet de vérifier d'un coup d'œil la fidélité de la reformulation.

## 2. Mise en page générale

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Barre supérieure :  💾 Sauvegarder · ❓ Aide · 🏠 Retour à l'accueil        │
│                      ▶ Traiter les blocs non validés · 💶 Coûts estimés     │
│                      A+ · A− (taille du texte — les deux colonnes)          │
├────────────┬─────────────────────────────────────────────────────────────┬──┤
│            │  TEXTE BRUT CORRIGÉ (v1)      │  BLOC REFORMULÉ (LLM)       │  │
│  Locuteurs │  (lecture seule + audio)      │  (éditable)                 │ ●│
│  (gauche)  │                               │                             │ ●│
│            │                               │                             │ ●│
│  Philippe  │                               │                             │ ●│
│  Daniel    │                               │                             │ ●│
│  …         │                               │                             │ ●│
├────────────┴─────────────────────────────────────────────────────────────┴──┤
│ TIMELINE de la réunion — composant v1 inchangé, ancrée en bas (masquable)    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Barre d'état : étude · réunion · X blocs validés / Y · progression           │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Colonne de gauche** : liste des locuteurs, comme dans l'éditeur v1 (sélection/filtrage par locuteur, surbrillance des blocs du locuteur survolé ou sélectionné). Un bloc fusionné multi-locuteurs apparaît chez chacun de ses locuteurs.
- **Zone centrale, deux colonnes** : une par paire « bloc brut ↔ bloc reformulé », FID identique, une **ligne par bloc** (hauteur de ligne = max des deux cellules ; l'alignement est par bloc, pas par paragraphe — les deux textes peuvent différer en longueur).
- **Colonne des pastilles** (fine, à droite) : une pastille par bloc, cliquable — état du bloc + menu contextuel (§5).
- **Barre supérieure** : boutons globaux — sauvegarde du projet, aide (manuel v1.0), retour à l'accueil, lancement du traitement (blocs non validés), coûts estimés avant lancement, **taille du texte A+/A−** (reprise de la v1 : agit simultanément sur les deux colonnes, mémorisée comme en v1), **📋 Log** (page Log des opérations, §8).
- **Barre d'état** : étude courante, réunion courante, compte des blocs (validés / total), progression d'un traitement en cours.

## 3. Colonne « texte brut corrigé » (gauche, par bloc)

Le texte brut est la **référence de relecture** : il provient de la transcription corrigée v1 et n'est jamais modifié depuis cette page.

- **aucun menu contextuel** dans cette colonne (les menus v1 — correction de mots, split/merge, renommage de locuteur — sont désactivés sur cette page, pas grisés : ils n'existent pas ici) ;
- **seules actions disponibles** :
  - **clic** dans le texte : positionner le curseur de lecture (et donc l'audio) à cet endroit ;
  - navigation via la **timeline** (voir ci-dessous).
- Lecture audio, surlignage du mot lu (E1.3 v1) et surbrillance du bloc joué restent actifs.

Le texte brut est en lecture seule permanente sur cette page ; le découpage se règle en amont, en préparation des blocs.

### Timeline — réutilisation stricte du composant v1

- **la même timeline que l'éditeur v1**, portant **toute la réunion**, réutilisée telle quelle — pas de composant par bloc, rien à réinventer ;
- rôle unique : **faciliter la navigation et le repérage** dans l'audio et la transcription ;
- positionnée **en bas de la page, ancrée** : le défilement vertical des colonnes **n'affecte pas son affichage** (elle reste visible, comme dans l'éditeur v1) ;
- **masquable** via un bouton de la barre supérieure — un traitement linéaire bloc par bloc ne nécessite pas toujours la navigation ;
- le curseur de lecture indique le bloc courant ; le bloc joué est surligné dans la table (les deux colonnes de sa ligne).

## 4. Colonne « bloc reformulé » (droite, par bloc)

- **Texte éditable** quand le bloc n'est pas validé (champ de texte riche multi-paragraphes, un seul retour à la ligne par paragraphe — normalisation du contrat) ;
- **bloc validé = figé** : édition et relances verrouillées ; seules opérations possibles : consulter les versions, dévalider ;
- sauvegarde au niveau du bloc (bouton + Ctrl+S sur le bloc ayant le focus) : **chaque sauvegarde d'une édition crée une nouvelle version** (`type: edition_manuelle` selon le contrat) ;
- la cellule signale les modifications non enregistrées (indicateur visuel) ;
- **reformulation partielle** : le texte reformé de la sélection est **intégré dans le bloc complet** (remplacement du passage sélectionné) ; c'est toujours **l'ensemble du bloc qui est versionné** (version `relance_ciblee`) ;
- indicateur de contrôle qualité du bloc (silhouette discrète : longueur, références, interdits stylistiques) au survol ou sur clic : détail des contrôles, sans bloquer l'édition.

## 5. Pastille de bloc, version et menu contextuel

Chaque bloc porte, à droite, **une pastille d'état** (clic = menu des opérations) et **l'indicateur de version** (ex. « v3 ») avec ses statistiques :

| État | Couleur pastille | Signification |
| --- | --- | --- |
| Non traité | grise | Aucun résultat LLM |
| En cours de traitement | bleue (animée) | Transitoire, pendant l'appel |
| **Modifiable** | bleue | Traité, non validé — édition et relances possibles |
| **Validé** | verte | **État figé** : alimente contexte, synthèse et ouvrage |

### Indicateur de version (affiché en dur, sous la pastille)

- **affichage permanent** (police compacte), pas seulement au clic : numéro de version (ex. `v3`) + stats de la version sur une ligne courte (ex. `12s · 3.1k→1.2k · 0,01 €` : durée, tokens entrée→sortie, coût estimé) ; les coûts API proviennent du catalogue de coûts par modèle des réglages de l'app (éditable, mise à jour régulière) ;
- **menu déroulant des versions** (déclenché depuis l'indicateur) : liste les versions existantes du bloc ; la sélection **remplace l'affichage de la cellule droite par la version demandée** (consultation) ; un retour à la version courante est toujours proposé ; la version affichée est clairement indiquée (ex. « v2 (consultée) »). L'édition ne se fait que sur la version courante.

### Menu de la pastille (et clic droit sur la cellule reformulée — menu identique)

1. **Éditer le bloc** — met le focus sur la cellule reformulée (bloc non validé) ;
2. **Sauvegarder le bloc** — crée la version `edition_manuelle` ;
3. **Retour arrière sur les modifications** — annule les modifications non sauvegardées (retour à la dernière version) ; une seconde invocation propose de revenir à la version antérieure (navigation dans l'historique) ;
4. **Reformuler le bloc…** — reformulation complète avec **boîte de dialogue de consigne complémentaire** (optionnelle) ; crée une version `relance` ;
5. **Reformuler le texte sélectionné…** — actif quand une sélection existe dans la cellule ; consigne optionnelle ; le passage reformé est intégré au bloc complet ; crée une version `relance_ciblee` ;
6. ---
7. **Valider le bloc** — fige l'état (pastille verte) et met à jour la synthèse d'étude ; **aucune relance en cascade proposée** : l'utilisateur relance individuellement les blocs qu'il estime devoir retoucher (décision 2026-10-27) ;
8. **Dévalider le bloc** — rebascule en modifiable (pastille bleue) ; les modifications redeviennent possibles.

Les items indisponibles dans le contexte (ex. « Reformuler le texte sélectionné » sans sélection, tout item sur un bloc validé sauf « Dévalider ») ne sont pas affichés ou grisés selon le contexte.

## 6. Comportements transverses

- **Sélection depuis la colonne locuteurs** : filtrer/surbriller les blocs du locuteur ; le bloc fusionné (multi-locuteurs) apparaît chez tous ses locuteurs et se réforme/valide une seule fois ;
- **défilement synchronisé** : les deux colonnes d'une même ligne défilent ensemble (une seule barre de défilement verticale pour la table) ;
- **tri figé** : l'ordre des blocs est l'ordre du découpage (chronologique) ; pas de réorganisation depuis cette page (l'ordre d'ouvrage est un objet P19) ;
- **lancement du traitement** : « Traiter les blocs non validés » lance la passe complète (avec estimation de coût, comme au niveau réunion) ; pendant le traitement, les pastilles traitées passent à l'état « traité, non vérifié » au fil de l'eau ;
- **raccourcis clavier** : Ctrl+S (sauvegarder le bloc au focus), Ctrl+Entrée (valider le bloc au focus) ;
- **accessibilité des états** : les couleurs de pastille ont toujours un libellé textuel au survol.

## 7. Règles d'invariance UI (à tester)

1. La colonne brute n'expose **aucune commande de modification** — ni active ni grisée : les menus contextuels v1 y sont désactivés ; seuls le positionnement du curseur (clic) et la timeline (curseur, zoom, masquage) réagissent.
2. Aucune opération ne modifie le texte brut d'un bloc ; toute écriture passe par la colonne reformulée et crée une version.
3. L'alignement brut ↔ reformulé se maintient au redimensionnement et à l'édition ; la timeline (composant v1, ancrée en bas) n'est jamais affectée par le défilement vertical des colonnes.
4. Un bloc validé est figé : aucune édition ni relance n'est possible tant qu'il n'est pas dévalidé ; les versions consultées d'un bloc validé ne peuvent pas être éditées.
5. Une validation n'est possible que sur une version sauvegardée (l'édition non sauvegardée est signalée ; la validation propose de sauvegarder d'abord).
6. Le filtrage par locuteur ne masque jamais le traitement en cours ni les indicateurs d'état de la barre d'état.

## 8. Log des opérations

### Principe

- **Fichier dédié associé à l'étude** (dossier de l'étude), journalisant **toutes les opérations** du process — pas seulement la reformulation : passes complètes, reformulations par bloc (relances, ciblées), éditions manuelles, validations/dévalidations, erreurs API, fusions de blocs, etc.
- Chaque entrée : horodatage, type d'opération, identifiant du bloc (FID), modèle utilisé, version produite, tokens entrée/sortie, durée, coût, résultat (succès/erreur).

### Page « Log » (icône 📋 de la barre supérieure)

- Nouvelle page in-app ouverte depuis l'icône **📋 Log** de la barre supérieure ;
- **lecture seule** : texte déroulant avec barre de défilement, pas d'édition ;
- **copie possible** (bouton « Copier tout » et copie d'une sélection) ;
- retour à la page précédente (reformulation) via le bouton retour habituel ;
- le contenu affiché est celui du fichier log de l'étude courante, rafraîchi à l'ouverture de la page.