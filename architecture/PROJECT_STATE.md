# PROJECT_STATE.md - Etat actuel du développement TranscriptStudio

> **Dernière mise à jour** : 2026-10-27 (session P14.5 — P14 CLOS)
> **Branche** : master
> **Modifications locales** : aucune (tout est commité)

---

## ETAT GIT

- Branche `master`, historique propre, commits de la session P14 (7) poussables
  (origin avait 5 commits de retard avant la session P14.5).
- v1 (P0 à P10, E1, E2) : **terminée et validée** — portabilité, mode sans clé API,
  résilience, tests.
- **P11 — Packaging Windows v1.0 : CLOS** (décision David, 2026-10-27) :
  Nuitka 4.3 standalone + Inno Setup per-machine + ZIP portable, manuel utilisateur
  v1.0, README complet (build, SHA-256, VirusTotal), licence GPL-3.0.
- **P12 : CLOS** : correctifs du binaire 1.0 (segfault Nuitka/PySide6 lambdas →
  functools.partial, FFmpeg embarqué, plugins Qt Multimedia), crash changement de
  thème (préchargement des feuilles de style), aperçu immédiat du thème, README
  (captures, VirusTotal 2/68).
- **P13 : CLOS** : message de fin d'export avec ouverture fichier/dossier.
- **P14 : CLOS** (P14.1 à P14.5 livrés et validés par l'atelier —
  ARBITRAGE_P14.md) — la feuille de route v2 à jour est
  `architecture/spec_v2/FEUILLE_DE_ROUTE_V2.md` (version 2026-10-27b) ; le
  contrat `CONTRAT_FORMAT_ETUDE_V2.md` (chemin_absolu et buffer contractualisés)
  fait autorité pour le format étude.

---

## SESSION 2026-10-27 — P14 : FORMAT ÉTUDE & FONDATIONS DONNÉES

Rituel de synchro effectué : assets spec/ recopiés dans `architecture/spec_v2/`
(lecture seule, jamais modifiés), PROJECT_STATE.md remonté vers
`G:\Mon Drive\TranscriptStudio\Synchro`.

### P14.1 — Format étude ⭐ TERMINÉ (commit 6794b64)

- `models/etude.py` : objets du contrat — `Etude` (etude.json), `ReunionEtude`
  (référence à un projet v1), `RegistreFID` (registre unique pour toute l'étude,
  FID séquentiels jamais réutilisés), `DecoupageReunion`/`BlocParole`
  (positions dans l'audio traité, source immuable, origine fusion/sous-découpage),
  `VersionReformulation` (validation portée par la version, stats LLM, contexte),
  `ResultatResume` (source stockée avec le résultat), `SyntheseEtude`
  (déclencheur), `ParametresEtude`.
- `services/etude_schema.py` : validation de schéma stricte de chaque fichier JSON
  (clés requises, types, énumérations, timecodes, cohérence du registre) ;
  `EtudeFormatError` avec fichier + message.
- `services/etude_io.py` : création/ouverture/sauvegarde d'une étude, réunions
  (ajout par référence, retrait, ordre), FID, découpage, résultats versionnés
  (jamais d'écrasement), résumés, synthèse, paramètres, résolution des chemins
  **relatif → absolu historique → relocalisation guidée**, **mode dégradé** (projet
  introuvable : l'étude s'ouvre sans bloquer).
- `services/timecodes.py` : timecodes `HH:MM:SS.mmm` du contrat + horodatage ISO.
- `resources/prompts/` : prompts v2 (reformulation, résumé) embarqués comme
  **valeurs actives par défaut** des paramètres d'étude (contrat §10). Aucune clé
  API en clair (cle_ref credential_store).
- `tests/unit/test_etude_format.py` : 34 tests, **dont les 5 règles d'invariance
  du contrat §12** (projet v1 intact à l'ouverture, FID/versions jamais écrasés,
  retrait d'une réunion sans toucher au projet v1 ni au registre, déplacement du
  dossier étude sûr, un projet v1 référencé par plusieurs études).

### P14.2 — Journal des opérations de prétraitement ⭐ TERMINÉ (commit 01a6610)

- `services/preprocessing_journal.py` : `journal_operations.json`, **fichier
  additionnel du dossier projet v1** (additif, non destructif) — opérations
  `decoupe` (positions), `silence_supprime` (position, durée originale, buffer),
  `acceleration` (facteur) ; **un nouveau journal remplace l'ancien** à chaque
  re-prétraitement ; présence optionnelle (projets antérieurs → None).
- Conversions **pures** `position_originale_vers_traitee` /
  `position_traitee_vers_originale` (secondes), règles de composition respectées :
  l'accélération s'applique aux positions post-suppression, les silences ne sont
  pas accélérés, positions/durées des silences dans le référentiel du discours
  original (pré-découpe).
- `duree_originale_pause(journal, position_traitee, seuil)` : durée originale de
  la pause à une position de l'audio traité, le buffer conservé étant accepté
  dans la marge — signal de coupe du P14.4.
- Intégration : `AudioProcessingPipeline` construit le journal au fil du
  `run()` ; le dialogue de prétraitement l'écrit dans le dossier projet à la fin
  du traitement (worker : signal finished à 3 arguments).
- `tests/unit/test_preprocessing_journal.py` : 19 tests (composition complète,
  aller-retours, frontières documentées, validation, pauses) dont 2
  d'intégration avec vrai FFmpeg (marqueur `slow`).
- Correctif au passage : `tests/unit/test_ffmpeg_resolver.py` rechargeait le
  module sous `sys.platform` patché **sans le restaurer** — la suite entière
  héritait de FFMPEG_NAME="ffmpeg" (contamination des tests qui exécutent
  réellement FFmpeg) ; rechargement restaurateur ajouté.

### P14.3 — Page Étude ⭐ TERMINÉ (commit da32b1b)

- Accueil : section **Études** (études récentes, « Nouvelle étude »,
  « Ouvrir une étude ») à côté des projets récents ; `SettingsManager`
  (get/add/remove/cleanup_recent_etudes).
- `ui/etude_window.py` : vue d'ensemble — réunions dans l'ordre de lecture avec
  statuts (joignable / projet introuvable / résumé validé), ajout de réunions
  (**projets v1 inchangés, référencés par chemin relatif avec fallback absolu**),
  ordre modifiable (Monter/Descendre), retrait (sans toucher au projet v1 ni au
  registre FID), **relocalisation guidée** pour un projet introuvable,
  ouverture de la réunion dans l'éditeur v1 existant, mode dégradé avec
  avertissement explicite.
- `tests/unit/test_recent_etudes.py` (3 tests) ; fumée offscreen de l'accueil et
  de la page Étude (y compris mode dégradé) validée.

### P14.4 — Découpage & sous-découpage automatique ⭐ TERMINÉ (commit 75075fd)

- `services/decoupage.py` :
  - segmentation depuis la diarisation validée du projet v1 (un bloc =
    intervention, locuteur, positions dans l'audio traité, source = texte du
    bloc non modifié) ;
  - **sous-découpage déterministe et local des monologues longs** : points de
    coupe candidats aux fins de phrase, scorés (pause longue du discours
    originel via le journal = signal principal ; marqueurs de transition
    « ensuite », « enfin », « deuxième »... ; fin de phrase), **pénalité absolue
    dans une citation biblique entre guillemets « »** ; sélection par
    programmation dynamique sous bornes de mots (600–900 par défaut,
    configurables) ; sans journal → scoring textuel seul ;
  - **ré-attribution des FID** (contrat §6) : bornes inchangées → FID conservé ;
    nouveaux blocs → nouveaux FID (jamais réutilisés) ; FID disparus →
    `actif: false` avec horodatage de fin (le FID reste au registre avec ses
    résultats).
- `tests/unit/test_decoupage.py` : 7 tests (fidélité à la diarisation, pauses
  réelles, jamais dans une citation, ré-attribution en re-segmentation stable et
  en bornes changées).

### Bilan tests

- **114 tests pytest verts** (`tests/unit`, exécution confirmée le 2026-10-27,
  environnement conda `transcript`, Python 3.11.15) : 30 v1 + 84 v2 (34 format
  étude, 19 journal, 3 études récentes, 7 découpage, 21 fusion/ordre d'ouvrage).
- Les 5 règles d'invariance du contrat sont couvertes par des tests dédiés.

---

## SESSION 2026-10-27 (suite) — P14.5 : FUSION ET ORDRE D'OUVRAGE ⭐ P14 CLOS

Rituel de synchro effectué sur les documents en vigueur (INDEX_SPECS.md) :
feuille de route 2026-10-27**b**, contrat 2026-10-27 (chemin_absolu et buffer
contractualisés), consignes 2026-10-27, ARBITRAGE_P14.md — **P14.1 à P14.4
validés par l'atelier, les 9 points arbitrés tous VALIDÉS**. Recopie locale
sous noms canoniques dans `architecture/spec_v2/`.

### P14.5a — Fusion de segmentation (commit P14.5)

- `fusionner_blocs(etude, réunion, fids_sources)` dans `services/decoupage.py` :
  fusion de blocs **adjacents** en un seul bloc de traitement — **nouveau FID**
  (jamais réutilisé), **locuteurs union** (ordre de première apparition,
  multi-locuteurs si besoin), **positions = bornes extrêmes**, **source =
  concaténation dans l'ordre chronologique** (jointure par espace),
  `origine.fusion_de` = FID sources dans l'ordre chronologique ;
- FID sources → `actif: false` avec horodatage de fin ; leurs **résultats
  restent attachés** ; les **blocs sources restent dans le découpage**
  (inactifs) — condition de la réversibilité : la dé-fusion restaure les
  **mêmes discours avec les mêmes FID** ;
- `defusionner_bloc` : le bloc fusionné quitte la segmentation active, son FID
  passe `actif: false` (jamais réutilisé, résultats conservés), les FID sources
  sont **réactivés** (`reactiver_fid` : actif=true, fin=null) ;
- garde-fous : au moins deux FID, sans doublon, présents et actifs, adjacents
  dans l'ordre chronologique (choix conservateur, cf. décisions) ;
- la segmentation **active** d'une réunion = blocs dont le FID est actif au
  registre (`blocs_actifs`).

### P14.5b — Ordre d'ouvrage par réunion

- `DecoupageReunion.ordre_ouvrage` : liste réordonnable de FID, **stockée en
  parallèle de l'ordre chronologique** (clé `ordre_ouvrage` du
  `blocs/decoupage/<réunion>.json`, absente = défaut chronologique) ;
- défaut = ordre chronologique des blocs actifs ;
  `definir_ordre_ouvrage` exige une **permutation exacte des blocs actifs**
  (pas de doublon, pas de FID inconnu ou inactif) ; `reinitialiser_ordre_ouvrage`
  revient au défaut ; `ordre_ouvrage_effectif` pour la lecture (P19 s'en
  servira pour la génération d'ouvrage) ;
- **tenu à jour par fusion/dé-fusion** : le FID fusionné prend la place des
  FID sources dans l'ordre stocké (et réciproquement) ;
- validation de schéma étendue (`valider_decoupage`) : liste d'entiers, sans
  doublon, FID présents dans le découpage.
- **UI (Monter/Descendre, glisser-déposer) : non réalisée** — aucune page
  n'affiche encore les blocs ; les boutons vivront naturellement dans la page
  Traitement de P16. La couche de données est complète et testée.

### Fusion de pensées : NON implémentée, conformément à l'arbitrage —
transférée en P19.4 (composition de l'ouvrage), rien n'a été fait à ce sujet.

---

## DÉCISIONS TECHNIQUES DE LA SESSION (P14)

1. **Champ additionnel `chemin_absolu`** dans `reunions/<nom>.json` : le contrat
   §4 impose un « chemin absolu historique stocké en secours à la première
   résolution réussie » mais son exemple ne le montre pas → clé ajoutée (None
   par défaut, remplie à la première résolution, persistée à la sauvegarde).
2. **Champ additionnel `buffer`** (secondes, nombre) dans chaque opération
   `silence_supprime` du journal : la feuille de route §3.1 exige la consignation
   du buffer conservé, et le P14.4 en a besoin (le silence résiduel de l'audio
   traité encadre la coupe) ; l'exemple du contrat §11 ne le montre pas.
3. **Sémantique des frontières de conversion** (documentée dans
   `services/preprocessing_journal.py`) : une position située dans la partie
   supprimée d'un silence se projette sur le début de la coupe ; la position
   exacte d'une frontière revient au début de la partie supprimée (choix
   conservateur ; les deux côtés d'une coupe partagent la même position traitée).
4. **Positions des silences du journal dans le référentiel du discours original**
   (pré-découpe) : les silences sont détectés sur l'audio découpé, le pipeline
   ajoute le décalage de découpe — conforme feuille de route §3.1.
5. **Doublon refusé au sein d'une étude** : le même projet v1 ne peut pas être
   référencé par deux réunions d'une même étude (`ajouter_reunion` lève une
   erreur) ; le contrat l'interdit *entre* études seulement, choix conservateur
   car FID et titres d'une même étude deviendraient ambigus.
6. **Journal écrit à la fin du traitement** (et non de la finalisation) dans le
   dossier projet : un re-traitement le remplace, un abandon supprime le
   dossier provisoire avec lui.
7. **Sous-découpage : signaux implémentés** = fin de phrase + pause du discours
   originel + marqueurs de transition + interdiction citation. Les signaux
   « fin de paragraphe » et « changement de référence biblique » de la feuille
   de route ne sont pas implémentés : le format v1 ne stocke pas de marqueurs de
   paragraphes, et le parsing de références arrive en P18 (JND).
8. **Page Étude → éditeur v1** : l'éditeur s'ouvre dans une fenêtre séparée ;
   son bouton Accueil revient à l'accueil général (pas à la page Étude) —
   navigation acceptable pour P14, à revoir en P16 si l'atelier le souhaite.
9. `resources/prompts/` doit être **inclus au prochain build packaging**
   (aux côtés de icons/ et du manuel) — pas de build v2 pour l'instant.
10. **Fusion limitée aux blocs adjacents** (P14.5) : la feuille de route dit
    « adjacents de préférence » ; l'adjacence est **imposée** — conservateur,
    elle garantit un bloc de traitement continu (bornes extrêmes, concaténation
    chronologique cohérente). À relâcher si besoin réel de fusion non adjacente.
11. **Blocs sources conservés dans le découpage** après fusion (inactifs) :
    la réversibilité exige que leurs textes/positions restent présents — le
    registre ne stocke pas les contenus. La segmentation active se lit via
    `blocs_actifs` (FID actifs au registre).
12. **Concaténation des sources par un espace** lors de la fusion ; les textes
    sources étant normalisés (sans espaces parasites), la jointure est propre.

## ÉCARTS / POINTS À ARBITRER PAR L'ATELIER

- ~~chemin_absolu, buffer, sémantique des frontières, doublon intra-étude,
  journal en fin de traitement, signaux de sous-découpage réduits,
  navigation Étude→éditeur, README/manuel~~ : **tous VALIDÉS par
  ARBITRAGE_P14.md** et intégrés au contrat v11 — plus en attente.
- Reste en observation : README et manuel utilisateur ne couvrent pas encore
  la section Études (report validé à la première livraison visible, P16 ou
  export v2).
- P14.5 : adjacence imposée (décision 10) et UI de l'ordre d'ouvrage renvoyée
  à P16 — les deux paraissent conformes à la feuille de route, arbitrage
  bienvenu si l'atelier voit autrement.

## NON RÉALISÉ (hors périmètre)

- **Fusion de pensées** : transférée en P19.4 (composition de l'ouvrage) par
  décision d'atelier — rien d'implémenté, conformément à la consigne.
- **UI de fusion et d'ordre d'ouvrage** (boutons Monter/Descendre,
  glisser-déposer) : couche de données complète et testée, l'UI viendra avec
  la page Traitement (P16).

---

## PROCHAINE ÉTAPE RECOMMANDÉE

**P14 est CLOS** (P14.1 à P14.5 livrés, validés par l'atelier).

1. **P15** — service LLM multi-fournisseurs
   (spec : PARAMETRAGE_LLM_V2.md ; familles openai_compatible/anthropic,
   catalogue embarqué extensible, CredentialStore, estimation de coût).
2. Puis **P16** — bloc Reformulation et page Traitement (spec :
   UI_REFORMULATION_V2.md), qui hébergera aussi l'UI de fusion et l'ordre
   d'ouvrage.

---

## RAPPEL DU CYCLE v1 (TERMINÉ)

P0 (first-run, découplage API, FFmpeg) → P1 (format projet portable v1) →
P2 (mode sans clé) → P3 (découplage finalisation/transcription) → P4 (résilience
media manquant) → P5 (nettoyage) → P6 (CredentialStore) → P7 (tests) →
P8 (résolveur FFmpeg hiérarchique) → P9 (UI multiplateforme : Fusion + qdarktheme,
icônes SVG teintées thème) → P10 (app_paths, temporaires par session) →
E1 (UX éditeur : surlignage animé du mot lu) → E2 (menu contextuel projets
récents) → **P11/P12/P13 (packaging Windows 1.0 + correctifs + export)**.

27+ tests v1 historiques toujours verts ; architecture multiplateforme en
place (aucune régression introduite par P14 : code nouveau isolé, pipeline v1
seulement étendu de façon additive).

---

*Ce fichier est mis à jour après chaque étape significative du développement.
Il est copié vers `G:\Mon Drive\TranscriptStudio\Synchro\PROJECT_STATE.md` à
chaque commit (hook post-commit) et lors du rituel de synchro.*
