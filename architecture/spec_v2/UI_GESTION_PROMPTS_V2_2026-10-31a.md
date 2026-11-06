# UI GESTION DES PROMPTS — P16-ter (2026-10-31a)

## 1. Contexte

Les prompts système (reformulation, résumé) vivent aujourd'hui
**en double** :

- valeurs **embarquées** de référence (`resources/prompts/
  prompt_reformulation_v2.md`, `prompt_resume_v2.md`) ;
- **copie active de chaque étude** (`parametres/parametres.json`,
  clés `reformulation.prompt` et `resume.prompt`), initialisée à la
  création de l'étude et déjà éditable (dialogue Paramètres de
  l'étude).

Il manque :

- une **bibliothèque de prompts** persistante, éditable dans les
  réglages de l'app ;
- une entrée **directe** depuis la page Reformulation et la page
  Résumé ;
- la **traçabilité du prompt effectif** de chaque version
  LLM (P20-ter a ajouté le modèle et ses paramètres ; le prompt
  reste invisible : deux versions ne se distinguent pas quand
  seul le prompt a changé).

## 2. Bibliothèque de prompts

- Dossier de paramétrage de l'app :
  `<données app>/prompts/` (même principe que le catalogue LLM,
  `services/llm/catalogue.py`).
- Un fichier par usage : `prompts/reformulation.md` pour la
  reformulation, `prompts/resume.md` pour le résumé (périphérie
  du format : texte Markdown brut, UTF-8).
- **Un usage sans fichier vaut le défaut embarqué** (`resources/
  prompts/…`). Aucune écriture au simple lancement de l'app ou à
  la lecture : le fichier n'existe que si l'utilisateur l'a
  créé.
- **Source d'initialisation des nouvelles études** :
  `parametres_par_defaut()` (services/etude_io.py) prend le
  prompt dans la bibliothèque — donc fichier
  `prompts/<usage>.md` s'il existe, défaut embarqué sinon.

## 3. Réglages de l'app — onglet « Prompts »

- Sélecteur d'usage (Reformulation / Résumé), éditeur multiligne
  intégré (QPlainTextEdit).
- Indication de l'origine courante : fichier bibliothèque
  (chemin) ou défaut embarqué, et hash court du texte.
- Actions :
  - « Réinitialiser aux défauts embarqués » : **suppression** du
    fichier `prompts/<usage>.md` (confirmation) — retour au
    défaut embarqué, sans réécrire quoi que ce soit d'autre ;
  - « Importer… » : charge un fichier `.md`/`.txt` dans
    l'éditeur de l'usage affiché (aucune écriture tant que
    « Enregistrer » n'est pas pressé) ;
  - « Exporter… » : écrit exactement le texte de l'éditeur au
    chemin choisi, extension `.md` ou `.txt`.
- « Enregistrer » (bouton global des réglages) écrit le contenu
  de l'éditeur dans `prompts/<usage>.md` pour chaque usage modifié.

## 4. Gestionnaire en mode étude

Un **bouton « ⚙ Prompts »** :

- page Reformulation : à **gauche** de « Traiter les blocs non
  validés » ;
- page Résumé : sur la ligne de lancement.

Il ouvre le gestionnaire **en mode étude** (usage de la page
présélectionné) :

- l'éditeur porte la **copie locale** (`parametres/<usage>.prompt`
  de l'étude) ; « Enregistrer » ne change QUE les
  paramètres de l'étude (`sauvegarder_etude`) ;
- **indicateurs de divergence (hash)** : hash court de la copie
  locale vs hash court de la bibliothèque (fichier, ou défaut
  embarqué si absent), libellé distinct « identique » /
  « divergent » avec les deux hashs ;
- actions avec confirmation :
  - « Recharger depuis la bibliothèque » : remplace le texte de
    l'éditeur par le texte de la bibliothèque (la copie locale
    n'est touchée qu'à « Enregistrer ») ;
  - « Promulguer dans la bibliothèque » : écrit le texte de
    l'éditeur dans `prompts/<usage>.md` (la bibliothèque n'est
    jamais touchée sans cette action explicite).

Les études existantes ne sont JAMAIS mises à jour par un
changement de bibliothèque : seule une nouvelle étude hérite de
la bibliothèque, ou une copie locale explicitement rechargée
(§6, invariant 3).

## 5. Traçabilité des versions

Chaque version LLM (reformulation ET résumé, aux deux points de
consignation — passe et relance ; génération, relance et relance
ciblée pour le résumé) **mémorise dans ses stats** :

- `prompt` : le texte intégral du prompt système **effectif** ;
- `prompt_hash` : les 8 premiers caractères hexadécimaux du
  SHA-256 du texte (hash court).

Le libellé de version de la page Reformulation affiche le hash
court (« prompt 8f2a1b3c »). L'historique déjà existant n'est
pas rétroactivement modifié.

## 6. Invariants

1. **Défauts embarqués intouchables.** Les prompts de référence
   de `resources/prompts/` ne sont jamais modifiés, ni par
   l'édition, ni par la réinitialisation (qui se contente de
   supprimer le fichier de bibliothèque), ni par
   import/export.
2. **Bibliothèque = dossier de paramétrage, lecture sans
   écriture.** La bibliothèque vit dans
   `<données app>/prompts/<usage>.md`. Un fichier absent vaut le
   défaut embarqué. Aucune lecture ne crée de fichier ; seules
   « Enregistrer », « Promulguer » et « Exporter » écrivent.
3. **L'étude garde sa copie.** Changer la bibliothèque ne
   modifie jamais les paramètres d'une étude existante ni ses
   traitements en cours ; une nouvelle étude hérite de la
   bibliothèque ; « Recharger depuis la bibliothèque » et le
   mode étude sont les seuls chemins vers la copie locale.
4. **Mode étude = copie locale uniquement.** Déposer par
   « Promulguer » écrit le texte local dans le fichier
   bibliothèque, après confirmation — jamais dans une autre
   étude, jamais dans les défauts embarqués.
5. **Traçabilité au fil de l'eau.** Chaque version LLM
   mémorise le texte effectif du prompt et son hash court ;
   l'historique existant reste tel quel (les versions sans
   hash ne sont pas réécrites).
6. **Import/export sans surprise.** L'import charge
   uniquement l'usage affiché dans l'éditeur et n'écrit rien
   tant que « Enregistrer » n'est pas pressé ; l'export écrit
   exactement le texte de l'éditeur, extension au choix
   `.md`/`.txt` ; aucun des deux ne touche une étude.

## 7. Livrables

- `services/prompts.py` : bibliothèque (lecture, écriture,
  réinitialisation, défaut embarqué, hash court).
- `ui/gestion_prompts_dialog.py` : panneau partagé + dialogue
  (modes bibliothèque et étude).
- Onglet « Prompts » des réglages ; boutons « ⚙ Prompts » des
  pages Reformulation et Résumé.
- `parametres_par_defaut` initialisé depuis la bibliothèque.
- Consignation `prompt`/`prompt_hash` dans les stats des
  versions (moteur reformulation, service résumé) + libellé de
  version.
- Tests des invariants 1 à 6 (tests/unit/
  test_p16ter_gestion_prompts.py).
