
# TranscriptStudio v2 — Feuille de route : Études, Traitements LLM et Reformulation

## 0. État du code (mise à jour par rituel de synchro)

> Référence d'avancement du développement. Sources de synchro : (1) `architecture/PROJECT_STATE.md`, copié vers le dossier Drive `TranscriptStudio/Synchro/` à **chaque commit** (hook git `post-commit`) et à chaque commande « synchronise avec agent de spec » dans le CLI ; (2) lecture du dépôt GitHub (code source). **Descente de la spec : skill partagé `transcriptstudio-spec`** dans le workspace Mistral « transcriptstudio » (consignes en corps, documents spec/ en assets, versionné — source de vérité de la descente ; le dossier Drive reste canal de montée et redondance). Relève côté atelier : **tâche planifiée quotidienne (9 h)** + **à la demande** (« synchronise » dans cette conversation). Circuit validé opérationnel le 2026-10-27.
>
> **Règle de propriété des documents** : `PROJECT_STATE.md` (mémoire de travail du CLI, état du code) et la feuille de spécification (intentions, écrite par l'atelier) restent **séparés**, avec un **monopole de publication chacun sur son canal** : le CLI écrit librement dans PROJECT_STATE.md (décisions techniques, contraintes découvertes en développant, écarts) sans jamais toucher aux feuilles de spec ; l'atelier est seul à écrire les feuilles de spec. La boucle se referme à la relève : si une décision technique notée par le CLI impacte les intentions, l'atelier l'intègre dans la feuille de route et republie par Drive. Le rituel de synchro du CLI est **générique** : tout fichier `*.md` du dossier Drive autre que PROJECT_STATE.md est un document de spec de l'atelier (toujours complet, jamais de fusion) ; les compléments arrivent en fichiers séparés ; le CLI recopie tout fichier nouveau ou plus récent dans `architecture/spec_v2/` (spec versionnée avec le code).

- **Dernière mise à jour connue** : 2026-10-29 — **relevé Drive PROJECT_STATE.md du 28/10 21h51 (contenu 29/10), sessions P16-bis (3 séries + terminologie), P17, P18, P18.5 et correctif « effort de raisonnement » du CLI** (branche v2, poussée sur origin/v2) : **P14 CLOS** (P14.1–P14.5, ARBITRAGE_P14) ; **P15 CLOS** (P15.1–P15.4, arbitrages B1/B1bis/B2/B3/C1/C2) ; **P16 LIVRÉ** ; **P16-bis LIVRÉ** (3 séries de correctifs UI + terminologie « réunion » d'affichage + navigation à pile unique AppWindow) ; **P17 LIVRÉ** (bloc Résumé + synthèse d'étude + récurrences) ; **P18 LIVRÉ** (JND OSIS locale, contrôle références/citations + alignement, export DOCX/TXT — P18.4 pré-correction NON réalisée, optionnelle) ; **P18.5 LIVRÉ** (téléchargeur de Bibles, version retenue par étude — défaut darbyR, versifications = information). **341 tests verts**. Correctifs intégrés : création d'étude en dossier non vide (ARBITRAGE_CREATION_ETUDE, variante b actée), génération du découpage exposée dans l'UI, clés LLM dans `credentials.json` avec migration automatique, catalogue v2 (GPT-5.6/6.x, Claude 5.5), effort de raisonnement mémorisé/restauré et transmis à l'API (niveaux jusqu'à « Très élevé », idem « Tokens max »). **origin/master vérifié resté à l'état v1 (P13, 74a6b09)** — le push accidentel P14 a été écrasé (`--force-with-lease`), rien à corriger.
- **v1 — état** : P0–P10, E1, E2 terminés ; **P11/P12/P13 clos** (packaging Windows 1.0 + correctifs binaire + message d'export).
- **v2 — état** : **P14 à P18.5 livrés** — reste **P18.6 — refonte de la navigation** (SPEC_NAVIGATION_V2_2026-10-29, maquettes validées par David), **la recette humaine P16/P17/P18 par David** (clé API réelle + jugement, checklist en fin de session P17 du PROJECT_STATE), puis **P19/P20 (v2.1)** : page Ouvrage de référence et édition avancée (fusion de pensées transférée en P19.4, mobilité des paragraphes, sous-titres IA, export structuré). Aucune régression v1 (code additif).
- **Écarts ou arbitrages en attente** : (1) **recette P16/P17/P18 par David** (réunion Luc 1b de bout en bout, fidélité, jonctions de méditation, « mémoire » de la 2ᵉ réunion, références vérifiables, export DOCX relu sous Word) ; (2) **édition de référence JND pour le contrôle qualité** (Darby vs DarbyR — arbitrage atelier bienvenu) ; (3) **P18.4 pré-correction** non réalisée (optionnelle, arbitrage) ; (4) **UI de fusion et d'ordre d'ouvrage** (couche de données complète, UI à placer en P19 ou arbitrage) ; (5) **fusion de pensées** transférée en P19.4 ; (6) **recherche des études limitée aux études récentes** (aucun registre global — à arbitrer si scan disque souhaité) ; (7) README/manuel utilisateur à la première livraison visible (P19/P20). Clos sans développement : création d'étude / transfert d'anciennes transcriptions (variante b, ARBITRAGE_CREATION_ETUDE validé par David).

## 1. Contexte et objectif

TranscriptStudio (dépôt `TranscriptStudio/TranscriptStudio`, branche `master`) est une application de bureau PySide6 / Python 3.11 organisée en couches : `models/` (contrats de format projet portable v1), `services/` (API ElevenLabs, export), `ui/` (accueil, prétraitement audio, éditeur avec timeline et diarisation).

La v2 ajoute une nouvelle capacité : transformer des transcriptions corrigées en textes rédigés (reformulation, résumé) via un LLM, avec deux niveaux de cohérence — à l'échelle d'une réunion et à l'échelle d'une « étude » (ouvrage regroupant plusieurs réunions sur un même thème). L'architecture doit rester généralisable (blocs de traitement configurables), mais la v2 se limite à deux blocs bibliques : **Reformulation** et **Résumé**.

Le prompt de référence du bloc Reformulation est le **Prompt de reformulation biblique v2** (document annexe, fourni séparément). Il fait foi pour le comportement rédactionnel : fidélité stricte, références bibliques complétées à bon escient, « nous » de foi conservé, « je » d'expérience personnelle aseptisé, citations JND, pas de gras, pas de titre, sortie = texte seul.

## 2. Principes directeurs (à respecter dans toute la v2)

1. **Non-destructif** : un traitement ne modifie jamais le texte source. Les résultats vivent à côté (calques). Le projet v1 reste lisible tel quel.
2. **Généralisation sans sur-ingénierie** : un bloc = nom + description + prompt système + périmètre (intervention / réunion / étude) + cases de contexte. Pas de chaînage de blocs, pas de scripting utilisateur en v2. Le pipeline (découpage, fenêtre glissante, exécution séquentielle, validation) est commun à tous les blocs.
3. **Validation humaine hybride, en deux régimes** :
   - **Passe complète** (défaut) : le moteur traite toute la réunion en une passe séquencée sans attendre l'utilisateur ; chaque bloc est reformulé avec, comme contexte, les résultats de la passe (frais, non encore validés) des blocs précédents ;
   - **Reprise à la demande** : si un bloc est édité ou régénéré après la passe, le moteur propose de relancer les blocs suivants ; lors de ces reprises, la fenêtre glissante n'utilise que du texte **validé** (ou corrigé) ;
   - option « mode strict » (par réunion) : traitement bloc par bloc, chaque bloc devant être validé avant de déclencher le suivant.
4. **Contexte sous budget** : chaque appel LLM envoie prompt système + fenêtre glissante (≤ ~2 000 tokens ; derniers résultats produits en passe complète, derniers résultats validés en reprise) + synthèse d'étude compacte (≤ ~1 500 tokens) + unité courante. Jamais une réunion entière en contexte répété. Activer le prompt caching côté fournisseur quand disponible.
5. **Vérifications locales, gratuites et exactes** : tout ce qui est vérifiable sans LLM l'est localement (rapport de longueur, références ajoutées, interdits stylistiques, texte JND). Le LLM ne sert qu'au langage.
6. **Fournisseur configurable** : le service LLM est multi-fournisseurs (Mistral, OpenAI, endpoint compatible OpenAI). Aucun couplage dur.
7. **Continuité de style de code** : suivre les conventions existantes (nommage, structure `models`/`services`/`ui`, messages de commit « Pnn - ... »), i18n français de l'UI, licence GPL-3.0, aucune dépendance payante embarquée.

## 3. Architecture cible

### 3.1 Nouvelle entité : l'Étude

L'étude est un **dossier** contenant ou référençant des réunions. Format proposé :

```text
MaEtude/
├── etude.json          # métadonnées, ordre des réunions, statuts, synthèse
├── synthese.txt        # synthèse d'étude (générée, régénérable)
└── reunions/
    ├── 2026-10-18_Luc01b/      # un projet TranscriptStudio v1 existant (copié ou lié)
    └── ...
```

`etude.json` (schéma indicatif) :

```json
{
  "format": 2,
  "titre": "Évangile selon Luc",
  "theme": "Luc 1",
  "ordre_reunions": ["reunions/2026-10-18_Luc01b"],
  "reunions": [
    {
      "chemin": "reunions/2026-10-18_Luc01b",
      "statut": "brute | corrigee | reformulee | validee",
      "synthese_locale": "synthese_reunion.txt"
    }
  ],
  "blocs": [
    {
      "id": "reformulation",
      "nom": "Reformulation",
      "prompt_systeme": "fichier ou texte (défaut : Prompt v2)",
      "perimetre": "intervention",
      "contexte": { "fenetre_glissante": true, "synthese_etude": true },
      "resultats": "reformulation/resultats.json"
    }
  ]
}
```

Points de conception :

- Une réunion reste un projet v1 autonome ; l'étude est un conteneur au-dessus. **Pas de migration du format v1** — compatibilité ascendante garantie.
- Les résultats d'un bloc sont stockés **par bloc de parole source** dans `resultats.json` :
  - clé = identifiant du bloc source (le bloc de diarisation, ou le sous-bloc en cas de sous-découpage) ;
  - chaque bloc de parole porte un **identifiant stable unique de type FID** (persistant, immuable), pour pouvoir manipuler les blocs au niveau étude sans dépendre d'index ou de chemins ;
  - chaque résultat contient : le lien vers le bloc source (FID), la **liste de toutes les versions** du résultat (chaque exécution ou relance de prompt crée une nouvelle version — jamais d'écrasement), la version courante, le statut (brouillon / validé), la date, le modèle, le coût estimé, les éventuelles instructions de correction saisies, les notes utilisateur ;
  - une version d'un résultat ciblé (sur sélection) est liée à la version parente et mémorise la portion visée.
- Plusieurs blocs de traitement coexistent sur les mêmes blocs de parole (reformulation et résumé ont chacun leurs résultats).

**Fusion de blocs** (besoin réel : deux interventions redondantes tout en se complétant, reformulées en un seul bloc) :

- action manuelle « Fusionner pour reformulation » sur deux blocs ou plus (adjacents de préférence) ;
- le bloc composé référence les FID des blocs sources (la fusion ne détruit rien : les blocs d'origine restent dans le projet, la fusion est réversible) ;
- texte source = concaténation dans l'ordre chronologique ; **attribution multiple aux locuteurs** concernés ;
- la reformulation traite le bloc composé comme une unité unique (le prompt v2 gère déjà la suppression des redondances en conservant les nuances complémentaires) ;
- à l'export, attribution affichée selon un réglage (« Philippe & Daniel », « Philippe, Daniel », ou un seul locuteur) ;
- l'ordre chronologique des traitements et du contexte reste fondé sur les positions d'origine.

**Découpage manuel des blocs multi-points** : l'éditeur v1 sait déjà séparer des blocs de parole — réutiliser cette fonction en amont de la reformulation. Lorsqu'un intervenant développe plusieurs points dans un même bloc, le découper en plusieurs blocs (aux jonctions naturelles : pause longue, changement de point) offre la bonne granularité : chaque sous-bloc est reformulé comme une unité cohérente et devient **déplaçable indépendamment dans l'ordre d'ouvrage**, sans casser la structure interne des blocs ni recourir à l'édition au paragraphe pour ré-harmoniser l'ensemble. Les blocs issus d'un même locuteur gardent la continuité dans la fenêtre glissante (le prompt sait que le discours est continu, comme pour le sous-découpage des monologues).

**Ordre de l'ouvrage** (l'ordre logique de lecture n'est pas toujours celui de l'oral) :

- chaque réunion porte deux ordres distincts : l'ordre chronologique (immuable — sert aux fenêtres glissantes, au contexte, à l'audio) et un **ordre d'ouvrage** (liste réordonnable des blocs validés, glisser-déposer, séparateurs de sections possibles) ;
- défaut : ordre d'ouvrage = ordre chronologique ;
- l'export assemble selon l'ordre d'ouvrage, avec aperçu de l'assemblage avant génération (vérification visuelle des renvois implicites devenus faux après déplacement) ;
- indicateur local optionnel : détection des expressions de renvoi (« comme on l'a dit », « cela a été rappelé »...) dans les blocs déplacés, signalée à l'utilisateur ;
- limite v2 : réorganisation au niveau du bloc uniquement ; réorganisation de paragraphes entre blocs = v3 éventuelle.

**Normalisation du texte des résultats** : les LLM renvoient généralement un double retour à la ligne entre paragraphes. Les résultats stockés et exportés conservent **un seul retour à la ligne** par saut de paragraphe (l'espacement entre paragraphes est géré par la mise en forme Word à l'export). La normalisation s'applique systématiquement à la réception du résultat du LLM.
- Une intervention = bloc de diarisation validé (même locuteur, plage continue), avec possibilité de sous-découpage manuel (chevauchement de contexte entre sous-blocs).

**Cas particulier : intervention unique longue** (méditation, lecture commentée, prédication — un seul locuteur pendant 20–40 min). L'intervention ne peut pas être traitée en un seul appel LLM. Le découpage est **déterministe et local** (pas de LLM) :

- génération de points de coupe candidats à chaque fin de phrase, scorés selon : **pause longue du discours originel**, reconstituée à partir du **journal des opérations de prétraitement audio persisté dans le projet** (l'information des silences supprimés n'est pas conservée aujourd'hui : il faut la stocker au moment du prétraitement). Le journal est une **liste ordonnée d'opérations** reflétant l'enchaînement réel : découpe début/fin (offset), suppression des silences (pour chaque silence : position, durée originale, buffer conservé), accélération (facteur) — avec les règles de composition : l'accélération s'applique aux positions post-suppression, les silences supprimés ne sont pas accélérés, les durées originales des silences restent exprimées dans le référentiel du discours original. L'app expose deux fonctions de conversion pures (position audio traité ↔ position originale), testées unitairement. Signal de coupe : un point situé à l'emplacement d'un silence originel de plusieurs secondes (le buffer conservé dans l'audio traité est déduit pour ne pas fausser la mesure) ; complété par : fin de paragraphe de la transcription, marqueurs de transition du discours (« ensuite », « enfin », « deuxième point », changement de référence biblique), pénalité forte à l'intérieur d'une citation biblique entre guillemets (ne jamais couper dedans) ;
- si le plan de coupe est absent (transcription importée, ancien projet) : scoring textuel seul (marqueurs, fins de phrase, citations) ;
- sélection des coupes par programmation dynamique sous contrainte de taille cible (~600–900 mots, bornes configurables), en maximisant le score des jonctions naturelles ; calcul instantané, déterministe, explicable ;
- repli possible : pré-appel LLM distant demandant des points de coupe (sans reformulation), si le découpage heuristique tombe manifestement mal ;
- chaque sous-bloc est traité séquentiellement avec la fenêtre glissante des sous-blocs précédents — exactement comme des interventions distinctes, mais le passage d'un sous-bloc à l'autre ne doit pas introduire de rupture stylistique (le prompt reçoit l'indication que le texte est continu) ;
- le résultat est stocké par sous-bloc, mais présenté et validé comme un texte unique reconstitué (l'utilisateur voit la méditation entière, pas des fragments) ;
- l'utilisateur peut ajuster les points de coupe manuellement avant la passe.

### 3.2 Service LLM (`services/llm/`)

- Interface `LLMClient` commune : `complete(system, messages, params) -> {texte, usage, cout_estime}`.
- Fournisseurs : Mistral, OpenAI, endpoint personnalisé compatible OpenAI (base_url + clé).
- Paramètres dans Réglages : fournisseur, clé API, modèle, température (défaut ~0.3), effort de raisonnement si applicable, « Tester la connexion ».
- Streaming pour affichage progressif ; comptage tokens et coût estimé par appel (comme dans `reformuler_gpt.py`).
- Gestion d'erreurs réseau, retry, annulation en cours de passe.

### 3.3 Moteur de traitement (`services/traitements/`)

Cœur partagé par tous les blocs :

1. **Découpage** : interventions depuis la diarisation validée ; sous-découpage automatique des interventions uniques longues (§3.1) et sous-découpage manuel.
2. **Assemblage du contexte** : prompt système du bloc + fenêtre glissante des N derniers résultats (produits en passe complète, validés en reprise) (+ résumé incrémental si la réunion est très longue) + synthèse d'étude (si cochée) + unité courante + éventuelles notes utilisateur.
3. **Exécution séquentielle** : une unité à la fois, dans l'ordre ; arrêt/annulation ; reprise à la demande.
4. **Contrôle qualité local** après chaque résultat (voir §5) : résultats stockés avec leurs indicateurs.
5. **Boucle de validation** : l'utilisateur relit, édite et valide chaque résultat après la passe ; en cas d'édition ou de régénération d'un bloc, reprise proposée des blocs suivants — lors de ces reprises, seuls les résultats validés (ou corrigés) entrent dans la fenêtre glissante.

Le moteur expose un **budget de contexte explicite** : chaque bloc déclare ses besoins, le moteur assemble dans la limite.

### 3.4 UI

- **Page d'accueil** : section « Études » à côté des projets récents (liste, création, ouverture).
- **Page Étude** : vue d'ensemble (réunions dans l'ordre, statuts, synthèse d'étude, accès aux traitements, export).
- **Page Traitement** (par réunion) : deux volets — bloc de parole oral (lecture seule, synchronisable avec l'audio si possible) ↔ résultat (éditable) ; navigation par intervention ; boutons « Traiter toute la réunion », « Régénérer avec consigne » (champ libre : plus concis, garder la question rhétorique…), indicateurs de contrôle qualité, validation.

**Outil d'édition du bloc de résultat** (pas mot à mot comme dans l'éditeur de transcription — l'audio n'est de toute façon plus synchronisé avec la reformulation, mais **à l'échelle du paragraphe**) :

- la transcription audio fournit des paragraphes par intervenant (bloc), mais la reformulation introduit généralement un sous-découpage en paragraphes propres : l'unité d'édition est donc le paragraphe du texte reformulé ;
- édition libre paragraphe par paragraphe (modification, fusion, scission, déplacement, suppression) ;
- **relance de reformulation ciblée sur une sélection de texte** du bloc : le contexte envoyé au prompt reste identique (bloc source + fenêtre glissante + synthèse d'étude), au détail près qu'on y ajoute la formulation courante du bloc **et toutes ses versions antérieures** — l'historique complet est conservé en contexte, sans limite de nombre, pour éviter que le LLM tourne en rond et revienne sur des corrections déjà rejetées ; la consigne de travail devient la reformulation ciblée de la sélection uniquement (le reste du bloc est conservé tel quel) ;
- cas des **reformulations partielles successives au sein d'un même bloc** (traiter le paragraphe 1, puis le paragraphe 2, etc.) : seules les versions du **paragraphe en cours de traitement** sont envoyées au prompt ; les versions antérieures des paragraphes déjà traités ne sont pas renvoyées, leur formulation validée servant simplement de contexte du bloc ;
- chaque relance (globale ou ciblée) crée une nouvelle version du résultat, conservée dans l'historique ; possibilité de revenir à une version antérieure ;
- validation du bloc (résultat figé pour l'export ; les blocs validés servent de fenêtre glissante lors des reprises des traitements suivants) ;
- **aide et bonnes pratiques** : l'aide en ligne et le manuel utilisateur doivent avertir que chaque version supplémentaire alourdit le contexte des relances suivantes (donc le coût) ; recommander de limiter le nombre de versions successives par bloc — notamment en éditant manuellement plutôt qu'en relançant lorsque la correction est mineure.
- Pas de nouvelle page de correction : l'éditeur existant reste l'étape de correction. Enrichissements prévus en P14-bis : pré-correction LLM légère des erreurs manifestes (noms bibliques, homophones) avec dictionnaire biblique local.

## 4. Blocs livrés en v2

### Bloc Reformulation (périmètre : intervention)

- Prompt système par défaut = Prompt v2 (fourni en annexe). **Prompt éditable dans les paramètres de l'étude** (valeur par défaut intégrée à l'app).
- Contexte : fenêtre glissante des reformulations validées + synthèse d'étude.
- Usage type : 5 000–6 500 tokens en entrée par appel, ~150 000–200 000 tokens d'entrée par réunion (ordre de grandeur, coût cible < 1 € par réunion selon fournisseur).

### Bloc Résumé (périmètre : réunion)

- Prompt système dédié (rédiger à partir du Prompt v2 en le spécialisant : condensé fidèle en prose, même niveau de langue, mêmes règles de références et de pronoms, sans introduire de pensée absente).
- **Source au choix, au lancement** :
  - depuis la **transcription brute corrigée** (vue d'ensemble rapide, sans attendre la reformulation) ;
  - depuis les **reformulations validées** (chemin recommandé : texte épuré, meilleur qualité/prix).
  - Le résultat stocke sa source dans les métadonnées (brute ou reformulée + date) ; un résumé fait sur la brute devient obsolète après reformulation → signaler à l'utilisateur si la source a évolué, sans mise à jour automatique.
- Pas de fenêtre glissante : la source est traitée en 3–5 gros segments avec léger chevauchement, puis assemblage.
- **Même outillage d'édition que la Reformulation** (mécanismes communs du moteur) : édition au paragraphe, relance complète avec instructions complémentaires (chaque relance crée une version, historique complet), relance partielle sur sélection (contexte identique + versions antérieures ; relances partielles successives : seules les versions du passage en cours sont renvoyées), validation, normalisation des retours à la ligne, avertissement coût dans l'aide.
- Longueur cible paramétrable (condensé court ou détaillé).
- Le résumé validé d'une réunion alimente la synthèse d'étude.

### Synthèse d'étude (mécanisme transverse)

- Générée/mise à jour à la validation d'une réunion (à partir des textes validés), régénérable à la demande.
- Contenu : thème, ordre, pensées déjà développées, versets déjà cités, points de vocabulaire récurrents ; ≤ ~1 500 tokens.
- Sert de contexte de niveau 2 à tous les blocs qui le cochent.

## 5. Contrôle qualité local (par résultat)

Sans LLM, affiché comme indicateurs/suggestions — jamais de modification automatique du texte :

1. **Rapport de longueur** : mots résultat vs mots source ; avertissement si > ~120 % (comme dans `reformuler_gpt.py`).
2. **Références bibliques** :
   - extraction des références du texte source et du résultat (parsing du format « Livre C.v » et variantes) ;
   - référence présente dans le résultat mais absente de la source → **suggestion de validation** : afficher le texte JND correspondant (via ressource locale, §6) pour vérifier que c'est bien le passage visé ; PAS une alerte d'erreur (la complétion est voulue) ;
   - référence présente dans la source mais absente du résultat → alerte discrète (vérifier qu'elle n'a pas été perdue).
3. **Interdits stylistiques** : recherche locale de motifs (« l'orateur », « le frère », « nous avons vu que », « il convient de », etc. — liste éditable).
4. **Citations** : correspondance citation ↔ référence avec le texte JND local ; écart signalé (paraphrase vs citation exacte), option « aligner sur le texte JND » à la demande.

## 6. Ressource JND (OSIS XML)

- Charger la Bible JND (et JND révisée) au format OSIS XML téléchargée librement ; fichier placé dans un dossier `resources/` (non suivi dans le dépôt si volumineux, avec instructions de téléchargement dans le README, comme FFmpeg).
- API locale : lookup (Livre, chapitre, versets) → texte ; recherche par expression ; parsing/normalisation de références (« genèse 2 verset 4 » → « Genèse 2.4-6 »).
- Utilisée par le contrôle qualité et l'éventuelle pré-correction.

## 7. Export de l'ouvrage (P18)

- Assemblage des textes validés dans l'ordre de l'étude (reformulations ; résumés de réunion en tête de section si souhaité).
- Export DOCX via python-docx (déjà présent) : styles sobres, guillemets “...”, références normalisées, en-tête de réunion optionnel ; pas de gras dans le corps.
- Réutiliser le flux d'export existant (message de fin, ouvrir le dossier).

## 8. Phases d'exécution

Convention de commit existante : `Pnn - <sujet> : <détail>`. Les phases v2 commencent à **P14**. Chaque phase doit être livrable et testable indépendamment. Écrire/mettre à jour les tests (`tests/`) au fil des phases, selon les pratiques existantes.

### P14 — Format Étude & fondations données

- P14.1 **Contrat complet défini dans le document « Contrat du format étude » (asset spec/CONTRAT_FORMAT_ETUDE_V2.md du skill transcriptstudio-spec) — il fait autorité pour l'implémentation.** Résumé : dossier étude référençant les projets v1 inchangés (résolution à l'ouverture, fallback, relocalisation) ; `etude.json` (titre, gabarit Titre 1, ordre des réunions) ; références de réunions ; **registre FID unique par étude** (FID jamais réutilisé) ; segmentation par réunion (source immuable, positions audio traité, fusion multi-locuteurs) ; résultats versionnés par bloc (contexte consigné) et par réunion (source du résumé stockée avec le résultat) ; synthèse versionnée ; paramètres (prompts v2 éditables, aucune clé en clair) ; **journal des opérations en fichier additionnel du projet v1** (`journal_operations.json`, remplacé à chaque re-prétraitement) ; règles d'invariance testées unitairement. + objets Python dans `models/` et validation de schéma.
- P14.2 Dossier d'étude : création, ouverture, liste des réunions (liens par chemin relatif, projet v1 inchangé), ordre, statuts.
- P14.3 UI : section « Études » sur l'accueil, page Étude (vue d'ensemble). Navigation accueil → étude → réunion (éditeur existant).
- P14.4 Découpage en interventions depuis la diarisation validée ; sous-découpage automatique des interventions uniques longues (méditations) en blocs traitables (~600–900 mots), signal principal = pauses du discours originel reconstituées via le **journal des opérations de prétraitement** (à persister dans le format projet : découpe, silences supprimés avec positions et durées originales, accélération ; l'information est perdue aujourd'hui, donc l'ajouter à la sortie du détecteur de silences et sérialiser au moment du prétraitement ; un nouveau journal remplace l'ancien à chaque re-prétraitement, pas de composition), conversions position traité ↔ original testées unitairement, scoring textuel en complément et en repli, coupes sans couper une citation biblique ; sous-découpage manuel ajustable (réutiliser la fonction de séparation de blocs de l'éditeur v1, y compris pour découper les blocs multi-points d'un même intervenant) ; stockage.
- P14.5 Fusion de blocs **de segmentation** (blocs mal découpés → un bloc de traitement : nouveau FID, `fusion_de` référencant les FID sources, multi-locuteurs, FID sources passant `actif: false` mais jamais réutilisés, réversibilité par réactivation des FID sources) et ordre d'ouvrage par réunion (par défaut = chronologique, réordonnable) avec stockage de l'ordre en parallèle de l'ordre chronologique.
- Critères d'acceptation : une étude se crée, référence des projets v1 existants, s'ouvre à nouveau sans perte ; un projet v1 seul reste utilisable sans étude ; le découpage reflète fidèlement la diarisation ; une méditation d'un seul intervenant est correctement sous-découpée sans couper une citation biblique ni un développement en cours.

### P15 — Service LLM multi-fournisseurs

> **Spécification complète définie dans « Spécification du paramétrage LLM » (asset spec/PARAMETRAGE_LLM_V2.md du skill transcriptstudio-spec) — fait autorité pour l'implémentation.** Résumé : deux familles d'adaptateurs (`openai_compatible` — OpenAI, Mistral, Groq, DeepSeek, xAI, OpenRouter, local Ollama/LM Studio — et `anthropic`), **catalogue embarqué + extensible** (fournisseurs, modèles, capacités, prix — le « catalogue de coûts » du contrat format étude), fournisseur par défaut OpenAI, clé par fournisseur via CredentialStore, « Tester la clé » + infos de compte quand l'API l'expose, UI de réglages adaptée aux capacités du modèle (température masquée si non supportée), surcharge par étude, estimation de coût avant passe et stats par version après, échec d'appel sans modification des documents, règles d'invariance testées.

- P15.1 `LLMClient` abstrait + implémentations par famille d'API (catalogue), streaming, usage/coût, retry/annulation.
- P15.2 Réglages : fournisseur, clé, modèle, température, effort de raisonnement, « Tester la connexion » (même UX que la clé ElevenLabs).
- P15.3 Moteur de traitement : assemblage de contexte (fenêtre glissante, budget), exécution séquentielle par unité, stockage des résultats et métadonnées (§3.3). **Spécification complète définie dans « Spécification du moteur de traitement » (asset spec/SPEC_MOTEUR_P15_V2.md du skill transcriptstudio-spec) — fait autorité pour l'implémentation.** Résumé des arbitrages : troncation de contexte par le haut (blocs les plus anciens de la fenêtre d'abord ; jamais synthèse ni unité courante), températures par défaut réglées dans l'app (reformulation 0.3, résumé 0.2) avec aide et surcharge par étude, confirmation/affichage du coût pour la première passe totale uniquement (pas de confirmation par bloc), annulation à mi-passe = conservation de tout ce qui est fait, reprise qui saute les blocs déjà traités, défaillance API = arrêt propre + reprise, aucune relance en cascade (décisions David du 2026-10-27).
- P15.4 Log des opérations (remplace le « journal de passe ») : fichier dédié `traitements/journal_operations.json` de l'étude, append-only, toute opération du process (passes, reformulations, relances, éditions, validations, fusions, erreurs API, annulations) avec horodatage, modèle, tokens, durée, coût ; page in-app « 📋 Log » en lecture seule depuis la barre supérieure (décision David du 2026-10-27) — contrat de stockage dans le format étude (§11), comportement dans SPEC_MOTEUR_P15_V2.md.
- Critères : une réunion traitée de bout en bout via un script de test ou un prototype de page ; coût estimé affiché ; annulation propre à mi-passe ; reprise possible.

### P16 — Bloc Reformulation (niveau 1) & UI Traitement

> **Spécification UI complète définie dans « Spécification UI — Page Reformulation » (asset spec/UI_REFORMULATION_V2.md du skill transcriptstudio-spec) — fait autorité pour l'implémentation.** Résumé : table de relecture en lecture parallèle (une ligne par bloc : texte brut corrigé à gauche avec lecture audio et timeline masquable — fonctions de correction v1 grisées ; bloc reformulé éditable à droite), colonne locuteurs à gauche, pastille d'état par bloc ouvrant le menu des opérations (éditer, sauvegarder = nouvelle version, retour arrière, reformulation complète avec consigne, reformulation de la sélection, valider/dévalider), boutons globaux (sauvegarde projet, aide, retour accueil, traitement des blocs non validés avec coûts estimés), barre d'état, défilement synchronisé, alignement maintenu au redimensionnement, règles d'invariance UI testées.

- P16.1 Intégration du Prompt v2 comme valeur par défaut éditable (paramètres de l'étude).
- P16.2 Page Traitement : volets source/résultat, navigation, traitement de toute la réunion, régénération d'une intervention avec consigne libre, édition manuelle, validation/refus.
- P16.2b Outil d'édition du bloc (§3.4) : édition au paragraphe, relance ciblée sur sélection (contexte identique + versions antérieures du bloc), historique de versions avec retour arrière, normalisation des retours à la ligne (un seul `\n` par saut de paragraphe), validation du bloc.
- P16.3 Fenêtre glissante : résultats produits en passe complète, résultats validés lors des reprises ; **aucune relance automatique en cascade** (décision David 2026-10-27 : si les blocs suivants sont bons, on ne les touche pas — l'utilisateur relance individuellement ce qu'il veut).
- P16.4 Contrôle qualité local (§5.1 et §5.3) affiché dans la page.
- Critères : réunion Luc 1b de test reformulée intégralement ; chaque résultat relisible face à sa source ; une intervention modifiée n'affecte que les suivantes après revalidation ; une méditation monologue est traitée en sous-blocs successifs sans rupture stylistique perceptible entre les jonctions.

### P16-bis — Correctifs de relecture UI (spec UI_REFORMULATION_MODIFS_V2.md — prime sur UI_REFORMULATION_V2 pour ces points)

Suite à la relecture de David (2026-10-27) : **défilement vertical unique et synchronisé** sur les deux colonnes, aucune barre de défilement interne aux blocs, hauteurs de ligne variables (blocs alignés horizontalement) ; **colonne locuteurs = noms par bloc** (une cellule par ligne, pas de cases à cocher ; le filtre est retiré de l'UI mais son API est conservée, réactivation future via menu de la barre supérieure) ; **zone gauche de la timeline de même largeur que la colonne locuteurs** ; **bouton « Reformulation… » dans l'éditeur v1** (actif si le projet appartient à une étude) ; **persistance de la taille de police** (A+/A− mémorisé dans les réglages, défaut abaissé pour la double colonne). 5 règles d'invariance additionnelles testées (spec §6).

### P17 — Niveau 2 : synthèse d'étude & bloc Résumé

- P17.1 Bloc Résumé (segments avec chevauchement, **prompt de résumé v2 fourni en annexe comme valeur par défaut éditable**), **source au choix à chaque lancement** (transcription brute corrigée ou reformulations validées, source stockée dans les métadonnées du résultat, avertissement si la source a évolué depuis) + outillage d'édition complet (§ Bloc Résumé) réutilisé du moteur commun ; longueur cible (650–700 mots par défaut) paramétrable au lancement.
- P17.2 Synthèse d'étude : génération à la validation d'une réunion, régénération à la demande, affichage dans la page Étude, injection comme contexte dans les blocs cochés.
- P17.3 Contrôle qualité étendu : comparaison des expressions récurrentes entre réunions (liste des formules les plus fréquentes de l'étude, à titre indicatif).
- Critères : résumé d'une réunion validée ; synthèse d'étude mise à jour ; une 2ᵉ réunion reformulée « sait » que la 1ʳᵉ a déjà développé telle pensée (comportement observable sur les rappels redondants, à juger humainement).

### P18 — JND locale, validation des références & export

- P18.1 Ressource OSIS XML (chargement, API lookup/recherche, normalisation de références, instructions README).
- P18.2 Contrôle qualité des références et citations (§5.2, §5.4) : suggestions de validation avec extrait JND, alerte de référence perdue, option d'alignement.
- P18.3 Export de l'ouvrage : DOCX (§7) ; éventuellement TXT/Markdown simples.
- P18.4 (optionnel) Pré-correction légère de la transcription avant traitement (dictionnaire biblique + LLM, suggestions uniquement).
- P18.5 **Addendum P18.1 (décision David 2026-10-28)** : téléchargeur de Bibles intégré aux réglages de l'app (Darby, Darby révisée, Segond 1910 ; sources BPC/concordance.bible, OSIS XML, jamais commité ; import manuel possible) + **version retenue par étude** (bloc `bible` de parametres.json, défaut `darbyR` — Darby révisée) + gestion des **versifications différentes** (écart signalé comme information, consultation des autres versions, jamais de décision automatique). Spec d'autorité : asset spec/BIBLE_JND_V2.md. Numéros Strong : hors v2 (v3 éventuelle).
- Critères : chaque référence ajoutée d'une réunion de test est vérifiable en un clic ; l'export DOCX s'ouvre proprement et s'intègre dans l'ouvrage final ; manuel utilisateur mis à jour (nouvelles sections Étude, Traitements, Export).

### P18.6 — Refonte de la navigation : hub, Réunion, Étude, Ouvrage (décision atelier 2026-10-29)

- P18.6a Hub d'accueil à 3 tuiles (Nouvelle transcription / Reprendre une réunion / Études), bandeau app réservé à l'accueil (logo, version, pastilles de services, ⚙, ?), dernières réunions en une colonne (stepper complet ①→⑥ conservé sur le hub — réunions autonomes).
- P18.6b Page Réunion : ruban (titre de réunion configurable, date · durée, badge étude · Bible, « Gestion de l'étude », Accueil, ⚙, ?) + stepper fixe ①→⑥, **④ Reformulation et ⑤ Résumé optionnelles** (contour pointé), « Étape suivante » + « passer l'étape › », passage direct ②→⑥ possible. ⑤ Résumé conservé (lecture en début de réunion suivante).
- P18.6c Page Étude : liste des réunions en une colonne (réordonnable), avancement ①→⑤ **sans ⑥** ; « Ajouter une réunion » (nouvel audio ou rattachement d'une réunion autonome) ; synthèse + récurrences (P17) ; renvoi export ouvrage vers la page Ouvrage.
- P18.6d Réunion objet de premier rang : autonome ou dans 1 étude — **exclusivité** (ARBITRAGE_EXCLUSIVITE_REUNIONS_2026-10-29, inverse l'invariant 13.5 du contrat republié 2026-10-29) ; rattachement à tout moment dès le prétraitement ; changement d'étude avec confirmation, les traitements restent à l'ancienne étude (option A).
- P18.6e **Saisie manuelle** : reformulations et résumés saisissables sans IA (copier-coller), statut « validé » équivalent, tracés au log des opérations.
- P18.6f Exports à 3 portées : réunion (⑥, y compris autonome/intermédiaire) / ouvrage (final, page Ouvrage) / résumé.
- Spec d'autorité : asset spec/NAVIGATION_V2.md (Drive : SPEC_NAVIGATION_V2_2026-10-29.md). Maquettes HTML validées = références visuelles.
- Critères : navigation à pile unique conservée ; invariants §9 de la spec testés unitairement ; aucune régression P16/P16-bis/P17/P18/P18.5 ; manuel mis à jour.

### P19 — Page Ouvrage de référence (v2.1)

Le document ouvrage est un **document dérivé autonome** : initialisé à partir des reformulations validées selon l'ordre d'ouvrage, chaque paragraphe conserve une **provenance** (FID du bloc source, réunion, date) ; ensuite l'ouvrage vit sa propre vie et **peut diverger** des textes validés par réunion (régénérer une reformulation ne met pas à jour l'ouvrage ; au mieux signalement « réunion re-reformulée depuis la génération »).

- P19.1 Modèle de données du document ouvrage : structure éditable (Titre 1 = paramétrable, ex. chapitre de l'évangile étudié ; sous-titres éventuels), métadonnées de réunion (numéro, date) **non structurelles**, paragraphes avec provenance. À prévoir dès P14 dans le format (même si la page n'existe qu'en P19).
- P19.2 Page Ouvrage : vue manuscrit compilée (toutes les reformulations validées de l'étude, ordre d'ouvrage), navigation par structure, édition de la structure (titres, sections, séparateurs).
- P19.3 Génération/rafraîchissement : générer l'ouvrage depuis les blocs validés ; régénération complète à la demande (écrase — avec avertissement) ; jamais de mise à jour automatique incrémentale.
- P19.4 **Fusion de pensées** (décision atelier 2026-10-27) : deux paragraphes dont les pensées sont très similaires (même locuteur ou locuteurs différents) peuvent être **fusionnés en un seul paragraphe** portant les **provenances multiples** (FIDs, locuteurs, réunions) — opération de **composition de l'ouvrage**, jamais de la page Reformulation (qui reste 1 bloc = 1 reformulation alignés, sans exception d'attribution). Fusion **manuelle** (éditeur côte à côte des deux textes) ou **assistée LLM** (relance avec les deux textes en entrée + consigne), **réversible** (dé-fusion : chaque paragraphe reprend son texte ; le paragraphe fusionné est conservé dans l'historique de l'ouvrage). Les paragraphes fusionnés survivent aux régénérations comme toute édition d'ouvrage. La détection des pensées similaires rejoint les aides à la relecture (P20 : redondances signalées par LLM à la demande).
- Critères : ouvrage généré pour une étude de 2+ réunions ; structure lisible indépendamment des réunions ; provenance consultable par paragraphe.

- Précisions maquette validée (2026-10-29) : la page Ouvrage présente trois zones — arborescence à gauche (largeur réglable, style Word : titres de chapitre ajoutés **manuellement** car l'enchaînement des réunions ne suit pas les chapitres, sous-titres manuels ou suggérés IA — cf. P20.2 —, réunions non placées en « Réserves »), document compilé éditable au centre, rapport d'analyse à droite (« Analyser la cohérence » à la demande : répétitions, incohérences, sujets récurrents — alertes navigables ; bouton « Re-vérifier les versets bibliques », redondance assumée avec le contrôle qualité de la reformulation).

### P20 — Édition avancée de l'ouvrage et aides IA (v2.1)

- P20.1 **Mobilité inter-blocs des paragraphes** : déplacement, fusion, suppression, édition libre des paragraphes à travers blocs et sections ; contrôle des renvois orphelins après déplacement (expressions « comme on l'a dit » etc., détection locale).
- P20.2 **Sous-titres proposés par IA** : appel LLM par section (« proposer 2 à 5 niveaux de sous-titres sobres pour structurer ce texte ») ; suggestions à valider/éditer, jamais insérées automatiquement ; coût marginal (une passe par section).
- P20.3 **Aide à l'écriture globale** :
  - **récurrence d'emphase** (intensifs et adverbes : « puissamment », « profondément », « véritablement »...) : la reformulation s'affranchit du style oral de l'intervenant, donc pas de comparaison source ↔ résultat — le contrôle porte sur **l'accumulation à l'échelle de l'ouvrage** : lexique paramétrable d'intensifs, comptage par bloc/réunion/intervenant sur l'ensemble des textes validés, signalement des densités anormales et des systématisations d'un bloc à l'autre (indicateur par bloc + vue transversale ouvrage) ; à l'utilisateur de trancher — un intensif bien placé reste une richesse — ; gratuit, sans LLM ;
  - expressions trop récurrentes : détection **locale sans LLM** (biais de reformulation en contexte limité) — mécanisme : normalisation (minuscules, ponctutation retirée, références bibliques masquées), extraction des n-grammes de 2 à 6 mots, comptage avec deux signaux : répartition (expression présente chez plusieurs intervenants/réunions = tic du reformateur ; concentrée dans une intervention = insistance légitime, ignorée) et écart à la fréquence attendue (pour ne pas signaler le vocabulaire du thème de l'étude) ; regroupement des variantes par mots communs (« ce qui s'offre à nos cœurs / à la foi »), avec passe LLM optionnelle à la demande sur la seule liste des familles candidates (coût minuscule) ; rapport = liste hiérarchisée d'expressions avec occurrences cliquables (navigation vers le paragraphe), **sans jamais suggérer de remplacement** — signalement humain seulement ;
  - trois portées : indicateur discret par intervention (déjà utilisée N fois dans l'ouvrage), petit rapport à la validation d'une réunion, vue dédiée ouvrage complet avec filtres (réunion, chapitre, intervenant) ;
  - incohérences et redondances : passe LLM par section (contrôle de cohérence étendu au chapitre), à la demande ;
  - dans tous les cas : signalement uniquement, jamais de réécriture automatique.
- P20.4 Export DOCX de l'ouvrage structuré (styles Titre 1 / sous-titres, métadonnées de réunion en note ou annexe selon réglage).
- Critères : paragraphes déplaçables entre sections avec provenance conservée ; sous-titres proposés et validables ; rapport de récurrences affiché sans coût LLM ; export fidèle à la structure éditée.

## 9. Risques et points de vigilance

- **Fenêtre de contexte** : surveiller le total (prompt + fenêtre + synthèse + unité) et l'ajuster par bloc ; prévoir le résumé incrémental pour les réunions longues.
- **Coût** : afficher le coût estimé avant une passe complète (l'utilisateur valide).
- **Répétition d'expressions** entre interventions/réunions : le niveau 2 atténue ; l'indicateur P17.3 aide à la relecture humaine. Ne pas automatiser de réécriture forcée en v2.
- **Erreurs de transcription** : les corrections manifestes par le LLM restent dans le cadre du prompt v2 ; en cas d'incertitude, ne pas inventer.
- **Compatibilité** : ne rien casser du cycle v1 (prétraitement → transcription → édition → export). Tous les ajouts sont des extensions.
- **Docs/manuel** : mettre à jour README et manuel PDF à chaque phase livrée (captures incluses).

## 10. Livrables finaux de la v2 (P14–P18) et v2.1 (P19–P20)

V2 :
1. Études créables, éditables, portables (dossier autonome).
2. Deux blocs de traitement (Reformulation, Résumé) avec prompts éditables et contexte hiérarchique.
3. Service LLM multi-fournisseurs avec coûts estimés.
4. Contrôle qualité local (longueur, références, style, citations JND).
5. Synthèse d'étude maintenable.
6. Export DOCX de l'ouvrage.
7. Tests, README et manuel utilisateur à jour.

V2.1 (page Ouvrage de référence) :
8. Document ouvrage dérivé autonome (provenance par paragraphe), structure éditable indépendante des réunions.
9. Mobilité inter-blocs des paragraphes, sous-titres proposés par IA (suggestions), aide à l'écriture globale (récurrences locales gratuites, incohérences/redondances par passe LLM à la demande).
10. Export DOCX de l'ouvrage structuré.

---

**Annexes à fournir séparément** :
- Prompt de reformulation biblique v2 (document de référence, valeur par défaut du bloc Reformulation) ;
- Prompt de résumé d'étude biblique v2 (document de référence, valeur par défaut du bloc Résumé ; source au choix brute ou reformulée, longueur cible 650–700 mots à exposer comme paramètre du bloc).