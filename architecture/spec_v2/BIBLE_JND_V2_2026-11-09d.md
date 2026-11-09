
# Addendum P18.1 — Téléchargeur de Bibles et version retenue par étude

Cet addendum complète la feuille de route (§6 « Ressource JND » et phase P18.1) suite aux constats de David (2026-10-28) : le CLI a imposé un fichier `JND.osys.xml` à installer manuellement, alors que les versions téléchargeables officielles se trouvent chez l'éditeur BPC ([editeurbpc.com/telechargements](https://editeurbpc.com/telechargements)) et sur [concordance.bible](https://concordance.bible). Il fait autorité pour l'extension de P18.1.

## 1. Versions supportées et sources

| Version | Identifiant | Source OSIS | Licence |
|---|---|---|---|
| Bible J. N. Darby (édition 2024, rév. 2.0) | `darby` | BPC — téléchargement direct OSIS XML | Domaine public |
| Bible J. N. Darby révisée (édition 2026, rév. 2.3) | `darbyR` | BPC — téléchargement direct OSIS XML | CC BY NC ND |
| Segond 1910 | `segond1910` | concordance.bible (à vérifier par le CLI : lien OSIS direct sinon import manuel) | Domaine public |

- Les **numéros Strong** (proposés par concordance.bible) sont **hors périmètre v2** — v3 éventuelle.
- L'app doit **vérifier l'URL de téléchargement** de chaque version au moment de la phase (BPC met à jour les fichiers ; révision mineure acceptée) ; en cas de lien cassé, le téléchargeur propose l'import manuel.

## 2. Téléchargeur intégré (réglages de l'app, section « Bibles »)

1. **Liste des versions disponibles** : nom complet, éditeur, édition/révision, licence affichée, état (installée / non installée), version installée vs disponible ;
2. **« Télécharger »** : télécharge l'OSIS XML depuis le site de l'éditeur, avec progression et gestion d'erreur réseau (message clair, aucun fichier partiel conservé) ; **aucun téléchargement silencieux ni automatique** — toujours à la demande ;
3. stockage dans le **dossier de ressources de l'app** (même mécanique que FFmpeg : hors dépôt git, dossier configurable, instructions README) — les fichiers Bible ne sont **jamais commités** (poids + licences) ;
4. **« Charger depuis un fichier… »** : import manuel d'un OSIS XML déjà téléchargé (première installation sans réseau, fichiers achetés/édités) ;
5. plusieurs versions peuvent cohabiter ; une version peut être réinstallée/remplacée (avertissement : les études qui l'utilisent relisent le nouveau fichier au prochain contrôle) ;
6. validation minimale du fichier à l'import : OSIS lisible, au moins un livre ; sinon message d'erreur explicite.

## 3. Version retenue par étude

1. **Réglage par étude** : `parametres/parametres.json` (contrat §10) porte un bloc `bible` : `{ "version": "darbyR" }` — identifiants ci-dessus ; **défaut : `darbyR`** (Darby révisée, décision David 2026-10-28, corrigée le même jour) ;
2. réglage accessible dans les paramètres de l'étude (déroulant) ; si la version choisie n'est pas installée dans l'app, message clair avec raccourci vers les réglages « Bibles » ;
3. **le contrôle qualité des références (P18.2) travaille contre la version retenue de l'étude** — jamais contre une version implicite ;
4. une étude sans bloc `bible` (études existantes) = défaut `darbyR`, sans migration.

## 4. Versifications différentes (Darby ↔ Darby révisée)

1. Les deux versions présentent des **versifications différentes** : une même référence peut exister dans l'une et pas dans l'autre (décalages de versets), et les orateurs peuvent citer selon l'une ou l'autre ;
2. quand une référence citée **n'existe pas dans la version retenue** de l'étude, le contrôle qualité **signale l'écart comme une information** (pas une erreur) : « Référence introuvable dans la version Darby — existerait-elle dans une autre versification ? » avec consultation possible du passage dans les autres versions installées ;
3. l'app ne décide jamais à la place de l'utilisateur : le choix de la version et le tranchement des écarts restent humains ;
4. la synthèse d'étude et l'export mentionnent la version retenue (métadonnées, pour la relecture) ;
5. **affichage (décision David du 2026-11-09, P18.9c)** : l'UI n'affiche **pas de champ « versification » distinct** — la versification découle de la version retenue (badge « Bible : Darby révisée », jamais « versification : … ») ; l'info-bulle du badge est épurée (libellé simple, aucun commentaire de spec) ; le traitement interne des écarts (points 1-3 ci-dessus) est inchangé.

## 5. Règles d'invariance (à tester unitairement)

1. Aucun fichier Bible n'est jamais écrit dans le dépôt git ni dans un dossier d'étude.
2. Une étude existante sans bloc `bible` s'ouvre sans migration et utilise la version `darbyR`.
3. Le contrôle qualité des références utilise toujours la version retenue de l'étude en cours.
4. Un téléchargement interrompu ne laisse aucun fichier partiel exploitable.
5. Changer la version d'une étude ne re-traité rien automatiquement : les écarts sont re-évalués au prochain contrôle qualité.
6. La page Bible (P18.10) n'écrit jamais dans un dossier d'étude ni dans un projet v1 ; seule exception : les réglages de l'app (dernier passage consulté).
7. Les sélecteurs chapitres/versets de la page Bible correspondent toujours aux données OSIS de la version affichée (jamais de compte en dur).
8. « Retour » depuis la page Bible ramène toujours à la page appelante (pile unique inchangée).
9. Un changement de version depuis le lecteur ne modifie ni la version de l'étude, ni celle du tier réunion, ni la référence d'uniformité de l'ouvrage (aucune écriture en retour, §8bis du CONTRAT_STOCKAGE_REUNIONS).

## 6. Livraison

Extension de **P18.1** (phase P18.5 dans la feuille de route) : téléchargeur + réglage par étude + gestion des versifications. Extension **P18.10** (décision David du 2026-11-09) : lecteur de Bible intégré (§7). Les tests utilisent des extraits OSIS fictifs ; la Bible réelle (déjà installée par le CLI) sert à la recette de David.

## 7. Lecteur de Bible intégré (P18.10 — décision David du 2026-11-09)

Page **consultative pure** de l'app : aucun LLM, aucun coût, aucune écriture (hormis les réglages).

1. **Accès** : icône sur la page Réunion, l'éditeur de transcription et la page Ouvrage ; navigation à pile unique, « Retour » ramène à la page appelante.
2. **Sélecteurs** : version → livre → chapitre → verset (facultatif, défaut v1) ; le verset est une cible de défilement/surlignage dans le chapitre affiché.
3. Les nombres de livres/chapitres/versets des sélecteurs **dérivent des données OSIS de la version sélectionnée** (versifications différentes, §4) — jamais de listes en dur.
4. **Dernier passage consulté** (version, livre, chapitre, verset) mémorisé dans les réglages de l'app et restauré à l'ouverture ; premier lancement = `darbyR` (défaut, §3), livre 1, chapitre 1, v1. Arbitrage David : la version proposée par défaut est la **dernière version consultée** (aucun lien automatique avec la version du contexte réunion/ouvrage, P20.5 demeurant inchangé).
5. **Saisie directe de référence** (ex. « Luc 1:5 ») réutilisant la normalisation P18.1 ; ambiguïté → suggestions de correspondances ; référence introuvable dans la version → écart signalé comme information (§4), consultation possible des autres versions installées.
6. **Versions affichables** = versions installées (§2) ; si aucune : message + renvoi vers le téléchargeur des réglages.