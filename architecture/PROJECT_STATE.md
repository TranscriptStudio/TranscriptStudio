# PROJECT_STATE.md - Etat actuel du développement TranscriptStudio

> **Dernière mise à jour** : 2026-10-30 (**P18.6-bis — correctifs
> de relecture de la navigation LIVRÉS, séries 1 à 4** : séries 1-3
> (grandes tuiles + « Version 2.0 », badge Bible court, dates de
> réunion, stepper compact après transcription, bouton unique) et
> série 4 du 2026-10-30e : tuile « Études » = menu déroulant
> ouvrant DIRECTEMENT la page Étude (page intermédiaire
> supprimée), CONTOURS VISIBLES et effet de survol (élévation
> ~2 px, bleu d'accent #4a7db5, ~120 ms) sur toutes les tuiles,
> 3 cartes en 3 colonnes ; reprise sur la maquette HTML validée
> (icônes SVG des 3 tuiles, métriques de carte, panneau déroulant
> stylisé : en-tête « Vos études », lignes d'études avec pastille
> de couleur + nom + thème · date de modification + badge
> « N réunions », séparateur, deux actions) ; sync documents du
> 2026-10-30d/e ; **442 tests verts**)
> **Branche** : v2 (développement v2 ; master reste à l'état v1, dernier commit P13)
> **Poussées** : en direct sur origin/v2 depuis le CLI (HTTPS + Git Credential
> Manager ; chaque poussée reste soumise à approbation)
> **Modifications locales** : aucune (tout est commité)

---

## ETAT GIT

- Développement v2 sur la branche `v2` ; origin/master vérifié resté à l'état
  v1 (P13, 74a6b09) — le push accidentel des commits P14 a été écrasé avec
  `--force-with-lease`, rien ne reste à corriger.
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
- **P15 : CLOS** (P15.1–P15.4, spec PARAMETRAGE_LLM_V2 + SPEC_MOTEUR_P15_V2 +
  ARBITRAGE_P15 : arbitrages B1/B1bis/B2/B3/C1/C2 appliqués).
- **P16 : LIVRÉ** (P16.1 paramètres d'étude, P16.2/P16.2b page Traitement
  Reformulation + page Log, P16.3 via moteur P15.3, P16.4 contrôle qualité
  local) — spec UI_REFORMULATION_V2 ; 188 tests verts.
- **P17 : LIVRÉ** (P17.1 bloc Résumé, P17.2 synthèse d'étude + cases de
  contexte, P17.3 récurrences entre réunions) — vérifié intégré
  après P16-bis (3 fumées test_p17_integration.py).
- **P18 : LIVRÉ** (P18.1 JND OSIS locale, P18.2 contrôle références/
  citations + alignement, P18.3 export DOCX/TXT de l'ouvrage ;
  P18.4 pré-correction NON réalisée — optionnel).
- **P18.5 : LIVRÉ** (téléchargeur de Bibles intégré, version retenue
  par étude, versifications — spec BIBLE_JND_V2_2026-10-28b) —
  334 tests verts.
- **P18.6 : LIVRÉ** (refonte de la navigation : hub 3 tuiles, page
  Réunion ruban + stepper ①→⑥ avec ④⑤ optionnelles, page Étude
  ①→⑤ sans ⑥ + réordonnancement, réunion objet de premier rang
  avec exclusivité 0-1 étude et changement d'étude option A, saisie
  manuelle sans IA, exports à 3 portées, page Ouvrage destination
  P19/P20 — SPEC_NAVIGATION_V2_2026-10-29b fait autorité,
  ARBITRAGE_EXCLUSIVITE_REUNIONS 2026-10-29) — 404 tests verts.
- **P16-bis : LIVRÉ** (correctifs de relecture UI, séries 1 à 3 +
  terminologie — UI_REFORMULATION_MODIFS_V2_2026-10-27d.md prime
  sur UI_REFORMULATION_V2 pour ses points).
- **P18.6-bis : LIVRÉ** (correctifs de relecture de la navigation,
  séries 1 à 4 — SPEC_NAVIGATION_MODIFS_V2_2026-10-30e fait
  autorité et prime sur SPEC_NAVIGATION_V2 et la version 30c
  pour ses points ; invariant 1 réécrit + 9 invariants
  complémentaires testés) — 436 tests verts.
- origin/master vérifié : resté à l'état v1 (74a6b09, P13), rien à réécrire.

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

## SESSION 2026-10-27 (P15, partie 1) — SERVICE LLM MULTI-FOURNISSEURS

Rituel effectué (Drive inchangé). **Développement sur la branche `v2`,
poussée en direct sur origin/v2** (paramétrage HTTPS + Git Credential
Manager autorisant le CLI à pousser après approbation). P15 démarre :
spec de référence PARAMETRAGE_LLM_V2.md (fait autorité).

### P15.1 — Catalogue + service LLM ⭐ TERMINÉ (commit c276992)

- `services/llm/catalogue.py` : **catalogue embarqué + extensible**
  (philosophie du résolveur FFmpeg P8) — défaut
  `resources/llm/catalogue_defaut.json` (OpenAI, Mistral, Anthropic :
  famille, capacités, prix exacts de la spec) ; stockage dans le dossier
  de paramétrage ; **réinitialisation reconstituant les défauts sans
  perdre les ajouts utilisateur** (règle d'invariance 3, testée) ;
  familles `openai_compatible` et `anthropic` ; prix = catalogue de
  coûts du contrat format étude ; fournisseur local (localhost) sans clé.
- `services/credential_store.py` : **credentials génériques** (une clé par
  fournisseur, `llm_cle_<id>`), interface ElevenLabs conservée.
- `services/llm/client.py` : client abstrait + adaptateurs
  **openai_compatible** (`/chat/completions` en SSE, `stream_options
  include_usage`) et **anthropic** (`/v1/messages`, événements SSE,
  `max_tokens` obligatoire → défaut 4096) ; **streaming** avec callback ;
  **usage réel** (fallback estimation locale si l'API ne le renvoie pas) ;
  **coût estimé aux prix courants du catalogue** (règle 5) ;
  **relance automatique avec backoff** (1 s, 2 s) sur erreurs transitoires
  (429, 5xx, réseau, timeout), aucune relance sur clé invalide ;
  **annulation propre** (avant l'appel et entre les chunks) ;
  **erreurs claires** (cle_invalide, quota, reseau, timeout, annulation,
  autre) — jamais d'exception brute, **la clé ne figure jamais dans un
  message** (règle 1, testée avec un corps de réponse qui la contenait) ;
  `tester_connexion()` (GET /models) pour le bouton « Tester la clé ».
- Tests : 31 (catalogue, clients avec session HTTP factice injectée,
  invariants 1/3/5).

### P15.2 — Réglages, onglet LLM ⭐ TERMINÉ (commit 8cdb96c)

- `ui/settings_dialog.py` refactoré en **onglets** (« Général » / « LLM
  (reformulation) ») : fournisseur du catalogue, **clé masquée une par
  fournisseur** (CredentialStore), « **Tester la clé** » avec état
  valide/invalide en couleurs, modèle, **température et effort de
  raisonnement affichés uniquement si déclarés par le modèle** (règle
  d'invariance 2), **max_tokens plafonné au contexte déclaré** ;
  fournisseur local : « aucune clé requise ».
- `ui/catalogue_llm_dialog.py` : **éditeur du catalogue** —
  ajout/suppression de fournisseurs et modèles, édition des prix et
  capacités, réinitialisation conservant les ajouts ; validation avant
  enregistrement.
- `SettingsManager.get_llm_config()/set_llm_config()` : sélection
  mémorisée app-wide (surchargeable par étude, contrat §10) ; **aucune clé
  dans les réglages** (CredentialStore seul, testé).
- Fumée offscreen complète : onglets, changement de fournisseur/modèle,
  masquage des réglages non déclarés, éditeur, mode first-run. 146 tests
  verts au total.

### DÉCISIONS / ÉCARTS DE LA SESSION (P15) — à arbitrer par l'atelier

1. **Infos de compte (spec §3.3)** : aucune API générique des deux
   familles n'expose solde/quota via un endpoint commun ; P15.2 affiche
   l'état de validité + le nombre de modèles accessibles (seul
   renseignement générique disponible) et masque la ligne pour les
   fournisseurs `endpoint_infos_compte: none` (Anthropic). Compléter
   par fournisseur si l'atelier le souhaite.
2. **Clé persistée au changement de fournisseur** : la clé saisie est
   mémorisée dans le CredentialStore dès le changement de fournisseur
   (et au clic Tester/Enregistrer) pour ne pas perdre la saisie — choix
   pragmatique à confirmer.
3. **Invariant 4 (échec sans modification des documents)** : garanti par
   construction au niveau du service (le client n'écrit rien, il
   retourne ou lève) ; le test d'intégration complet au niveau
   moteur/étude viendra avec P15.3.
4. **Estimation de tokens avant passe** : heuristique ~4 caractères par
   token (l'usage réel de la réponse API alimente toujours les stats
   stockées).
5. **`stream_options: include_usage`** envoyé aux familles
   openai_compatible ; si un endpoint local strict le refusait, le
   rendre conditionnel (suivi à l'usage réel).

### NON RÉALISÉ DANS P15 (suite de la phase)

- **P15.3** — moteur de traitement : assemblage de contexte (fenêtre
  glissante, budget), exécution séquentielle par unité, stockage des
  résultats et métadonnées.
- **P15.4** — journal de passe : par intervention, tokens in/out, coût,
  durée.
- Critères de fin de P15 (réunion traitée de bout en bout, coût estimé
  affiché, annulation à mi-passe, reprise) : évaluer avec P15.3/P15.4.

---

## SESSION 2026-10-27 (P15, partie 2) — MOTEUR + LOG : P15 CLOS

Rituel v13 effectué : SPEC_MOTEUR_P15_V2.md (nouveau, fait autorité),
ARBITRAGE_P15.md (7 points P15.1/P15.2 tous validés, décisions
B1/B1bis/B2/B3/C1/C2 intégrées), contrat v13 (§10 températures, §11 log des
opérations, §13 règle 6), feuille de route à jour — tout recopié dans
`architecture/spec_v2/`. **origin/master vérifié : déjà à l'état v1 (74a6b09)**
— la réécriture demandée par l'arbitrage §4 avait été faite la veille ; rien
à réécrire.

### P15.3 — Moteur de traitement ⭐ TERMINÉ (commit a3f5797)

`services/traitements/moteur.py` (MoteurTraitements), strictement selon
SPEC_MOTEUR_P15_V2.md :
- **assemblage** (§2) : prompt système → synthèse d'étude → fenêtre glissante
  (≤ 2 000 tokens paramétrable ; résultats **produits** en passe, **validés**
  en relance) → unité courante → consigne ; **budget explicite** contre le
  contexte du modèle du catalogue ;
- **troncation par le haut** (C1) : les plus anciens de la fenêtre d'abord ;
  jamais la synthèse ni l'unité courante ni le prompt ; si l'unité seule ne
  tient pas → erreur propre, bloc signalé (sous-découpage) ;
- **températures** (C2) : surcharge étude (parametres.json §10) sinon réglage
  app (reformulation 0.3 / résumé 0.2 dans les réglages, texte d'aide à venir
  en P16) ; envoyée uniquement si le modèle la supporte ; jamais codée en dur ;
- **exécution séquentielle** chronologique ; **estimation de coût avant la
  première passe totale** (B1 : fait office de confirmation, aucun dialogue,
  aucune confirmation par bloc — relances directes) ;
- **annulation propre** (B2) : arrêt à la fin de l'appel en cours (résultat
  conservé), tout ce qui est produit est versionné, journalisée avec position
  d'arrêt et résultats conservés ;
- **reprise** (§3.3) : saute les blocs traités, reprend au premier sans
  résultat ; **aucune cascade** (B3) ; commande explicite
  « blocs non validés » disponible ;
- **défaillance API** (§3.4) : retry du client puis arrêt propre, erreur
  consignée avec le message du fournisseur, résultats conservés ;
- **relance ciblée** : contexte identique + formulation courante + toutes les
  versions antérieures du bloc (mécanisme P16.2b en place au niveau moteur) ;
- le contexte utilisé est consigné dans la version (`contexte`, contrat §7) ;
  sauvegarde de l'étude après chaque bloc traité (durabilité).

### P15.4 — Log des opérations ⭐ TERMINÉ (commit a3f5797)

`services/traitements/journal.py` (JournalEtude) — décision B1bis, remplace le
« journal de passe » : `traitements/journal_operations.json` (contrat §11),
**append-only**, **écrit à chaque opération** (survit à un crash), types
passe_complete / reformulation_bloc / edition_manuelle / validation /
devalidation / fusion_blocs / erreur_api / annulation_passe / resume /
synthese. Toutes les opérations des services d'étude sont journalisées
(règle d'invariance 4) : versions de reformulation, éditions manuelles,
validations/dévalidations, fusions/dé-fusions, résumés, synthèses.
Document d'audit uniquement — jamais consommé par le moteur.
Page Log (spec UI §8) : **reportée en P16**, comme l'atelier y autorise.

### Bilan tests : **163 tests verts** (146 + 17)

Les **6 règles d'invariance de SPEC_MOTEUR §6** sont couvertes par des tests
dédiés (appel échoué sans écriture — invariant 4 du P15.1 exigé par
l'arbitrage ; annulation conservative ; troncation correcte ; exactement une
entrée de log par opération ; température effective jamais codée en dur ;
reprise sans re-traitement), plus la règle 6 du contrat §13 (le log ne perd
jamais une entrée) et les critères P15 de la feuille de route (réunion de bout
en bout, coût estimé, annulation, reprise — client LLM factice injecté).

### DÉCISIONS / ÉCARTS DE LA SESSION (P15.3/P15.4) — à arbitrer par l'atelier

1. **Message utilisateur unique à sections** : le contexte est assemblé en
   un seul message (synthèse / fenêtre / unité / consigne), le prompt système
   restant séparé — la spec fixe l'ordre, pas le découpage en messages.
2. **« Bloc déjà traité »** (spec §3.3) : interprété comme « possédant au
   moins une version » (conforme à « reprend au premier bloc sans
   résultat ») ; un bloc édité à la main n'est jamais retraité
   silencieusement.
3. **Dé-fusion au log** : journalisée sous le type `fusion_blocs` avec champ
   `defusion: true` (le contrat §11 ne liste pas de type dédié).
4. **Champs des entrées** : les compléments (statut, nb_blocs, cible,
   fids_sources, defusion...) sont fusionnés à plat dans l'entrée — style de
   l'exemple du contrat §11, pas de sous-objet.
5. **Synthèse d'étude** : incluse systématiquement quand une version existe ;
   le « si cochée » de la spec attend les cases de contexte de la page P16.
6. **Modèle par étude** (contrat §10) : résolu chez le fournisseur des
   réglages app ; si le modèle surchargé n'existe pas chez ce fournisseur,
   repli sur le modèle des réglages. Pas de surcharge fournisseur par étude
   (non prévue par le contrat).
7. **Journal créé vide** à la création d'étude ; une étude antérieure sans
   journal démarre un log vide (créé à la première opération).
8. **Sauvegarde après chaque bloc traité** (durabilité des résultats en
   cas de crash pendant la passe).

### NON RÉALISÉ (reporté)

- **Page Log en lecture seule** (spec UI §8) : P16.
- **Contrôle qualité local** (§5 du moteur) : P16.4/P18 comme prévu.
- **Bloc Résumé** au moteur : P17 (les types de log et l'outillage sont prêts).

---

## SESSION 2026-10-27 (P16) — BLOC REFORMULATION + PAGE TRAITEMENT : LIVRÉ

Spec de référence : `architecture/spec_v2/UI_REFORMULATION_V2.md` (fait
autorité), moteur P15.3 inchangé. Deux commits : cb1e363
(P16.1 + P16.4), 114bf49 (P16.2/P16.2b).

### P16.1 — Paramètres de l'étude ⭐ TERMINÉ (cb1e363)

`ui/parametres_etude_dialog.py` : prompts v2 (reformulation + résumé,
valeurs par défaut intégrées, réinitialisables), modèle et températures
surchargeables (contrat §10), fenêtre glissante, interdits stylistiques
éditables ; defaults dans `services/etude_io.parametres_par_defaut`.

### P16.2/P16.2b — Page Traitement ⭐ TERMINÉ (114bf49)

- `ui/reformulation_window.py` : table de relecture en lecture parallèle
  (brut lecture seule **sans aucun menu v1**, reformulé éditable), colonne
  locuteurs avec filtrage (ne masque jamais barre d'état ni boutons),
  pastilles d'état avec menu des opérations (édition, sauvegarde = nouvelle
  version `edition_manuelle`, retour arrière figé, reformulation complète
  avec consigne, reformulation de sélection, valider/dévalider sans
  cascade), indicateur de version permanent (v + durée + tokens + coût),
  passes en QThread avec annulation propre (B2) et coût réel (B1), bloc
  validé figé, timeline v1 ancrée masquable + audio (clic = positionnement,
  surlignage du mot lu), normalisation `\n` unique.
- `ui/log_window.py` : page Log en lecture seule avec copie (spec UI §8).
- `ui/etude_window.py` : bouton « Reformulation… » par réunion.

### P16.3 — Fenêtre glissante : couverte par le moteur P15.3

La page traite les blocs non validés via le moteur ; les reprises
n'utilisent que du texte validé.

### P16.4 — Contrôle qualité local ⭐ TERMINÉ (cb1e363)

`services/controle_qualite.py` : rapport de longueur (seuil 120 %),
interdits stylistiques (liste éditable), signalement uniquement.

### Bilan tests : **188 tests verts** (163 + 14 contrôle qualité + 11 UI)

Les invariants UI spec §7 sont couverts par `tests/unit/test_reformulation_ui.py`
(offscreen, marqueur qt) ; contrôle qualité par `test_controle_qualite.py`.

### DÉCISIONS / ÉCARTS DE LA SESSION (P16) — à arbitrer par l'atelier

1. **Page Log en QDialog** (fenêtre dédiée) plutôt que page intégrée ;
   lecture seule + copie.
2. **Surlignage du mot lu** : projection des mots horodatés v1 sur la cellule
   brute par jetons non-espaces ; si le nombre de jetons diffère (texte
   corrigé), repli au bloc sans surlignage mot à mot.
3. **Clic colonne brute → positionnement audio** au mot près (approximation
   par jetons, même limite que le surlignage).
4. **Pas d'affichage streaming dans la table** : pastille « en cours »
   transitoire seulement (la spec §3 ne l'exigeait pas ; coût/graisse d'UI
   jugés non justifiés en table).
5. **Validateur par défaut = utilisateur OS** (`getpass.getuser()`) — la
   spec ne fixait pas la valeur par défaut du champ validateur.
6. **Synthèse d'étude non mise à jour à la validation d'un bloc** : la spec
   §5 du menu pastille mentionne « met à jour la synthèse d'étude » —
   reporté à P17 (la synthèse n'existe pas encore comme mécanisme UI).
7. **UI fusion / ordre d'ouvrage** (Monter/Descendre) non ajoutée dans la
   page Traitement : les services existent (P14.5), l'UI reste à brancher
   si l'atelier la veut en page Reformulation ou en page Ouvrage (P19).
8. **Bouton « Paramètres » de la page Étude** : ParametresEtudeDialog est
   livré en dialogue autonome mais pas encore ouvert depuis la page Étude —
   à brancher (élément UI mineur).

### NON RÉALISÉ (reporté)

- **Bloc Résumé + synthèse d'étude** : P17 (moteur et log prêts).
- **Contrôle qualité §5.2/§5.4 (références, citations)** : P18 (JND).
- **Manuel utilisateur / README section Études** : report validé à la
  première livraison visible.

---

## SESSION 2026-10-27 (P16, correctifs post-livraison)

Retours utilisateur après livraison P16 ; 4 correctifs, 192 tests verts.

### 1. « Tester la clé » : erreur 504 affichée comme « Clé invalide »

- `ui/settings_dialog.py` : le libellé distingue désormais les types
  d'erreur — seul `cle_invalide` (401/403) affiche « Clé invalide » ;
  réseau/serveur (5xx) → « Test impossible pour le moment (erreur réseau
  ou serveur) » ; quota → « Limite d'appels atteinte ».
- `services/llm/client.py` : `tester_connexion` relance les erreurs
  transitoires (5xx, quota) comme les complétions (3 tentatives, backoff)
  — les deux familles (openai_compatible et anthropic). Le message
  « La tentative sera relancée automatiquement » devient exact aussi
  pour le bouton de test.

### 2. Études parasites sur l'accueil (9 entrées « Etude »)

- Origine : fumées UI de développement — `EtudeWindow` écrivait les
  études récentes dans le `SettingsManager` **réel** (les dossiers
  pointaient vers des temporaires pytest `Temp\tmp...`).
- Purge effectuée dans la config réelle de l'utilisateur : 9 entrées
  supprimées + dossiers temporaires effacés ; liste des études vides.
- Prévention : `EtudeWindow(dossier_etude, settings=None)` accepte un
  `SettingsManager` injectable (tests/fumées = config isolée).
  `HomeWindow` non modifié (lecture + nettoyage seulement).

### 3. Catalogue LLM v2 : familles GPT-5.6 / GPT-6.x (retour utilisateur)

- `resources/llm/catalogue_defaut.json`, `catalogue_version` 2 :
  - OpenAI : **gpt-6-astra** (10/50 $), **gpt-6.1-sol** (2/10),
    **gpt-6.1-terra** (1/5), **gpt-5.6-sol** (4/20, promo jusqu'au
    2026-11-21), **gpt-5.6-terra** (2/12), **gpt-5.6-luna** (0,20/1,20),
    gpt-4.1 conservé (2/8) ;
  - Anthropic : **claude-opus-5-5** (4/20), **claude-sonnet-5-5** (2/10),
    claude-sonnet-4 conservé ;
  - Mistral : mistral-large-latest (alias Large 4), prix actualisés
    1,36/4,18 $ (au lieu de 2/6).
- **Capacités** : les modèles de raisonnement GPT-5.6/6.x déclarent
  `temperature: false` + `effort_raisonnement: true` (l'API OpenAI
  rejette la température en 400 sur ces modèles) — le moteur n'envoie
  jamais la température à un modèle qui ne la déclare pas (déjà couvert
  par P15.3, règle vérifiée par test).
- **Mise à jour automatique** : `charger_catalogue` fusionne les
  nouveaux défauts quand la version stockée est plus ancienne que
  l'embarquée (fournisseurs « defaut » remplacés, ajouts « utilisateur »
  conservés, fichier réécrit) — l'utilisateur voit les nouveaux
  modèles sans « Réinitialiser ». « Réinitialiser » garde son
  comportement.
- 4 tests : retry 504 (openai_compatible : succès après relance +
  épuisement), retry 503 (anthropic), fusion de version du catalogue ;
  test des prix/capacités du catalogue v2 mis à jour.

### 4. Question d'architecture — étude conteneur des transcriptions

L'utilisateur demande si le dossier projet ne pourrait pas être le
conteneur étude (« toutes les transcriptions dedans »). Analyse CLI :

- **Rien ne bloque techniquement** : les réunions sont référencées par
  chemin relatif — un `etude.json` posé dans le dossier parent des
  projets (« Evangile de Luc/ ») référencerait les sous-dossiers
  projets tels quels, sans copie ni duplication.
- **Bloquant actuel** : `creer_etude` exige un dossier vide ou
  inexistant ; l'UX de création crée toujours un dossier dédié.
- **Avantages** : un seul dossier à déplacer/sauvegarder, aucun lien
  cassé, cohérent avec le croquis initial de la feuille de route §3.1
  (« reunions/ … copié ou lié »).
- **Risque à arbitrer** : copier les projets dans l'étude (option
  « conteneur autonome » du contrat) duplique les projets — divergence
  possible entre la copie et l'original ouverts indépendamment. La
  variante « référencer en place dans le dossier parent » n'a pas ce
  défaut et respecte « projet v1 inchangé ».

**→ Arbitrage atelier souhaité** : (a) étude dans un dossier dédié
(actuel), (b) étude créée dans le dossier existant des transcriptions
(références en place, `creer_etude` à assouplir), (c) copie des projets
dans `reunions/` (dossier autonome, gestion de la divergence à prévoir).
Recommandation CLI : (b) — petit changement, gros gain de portabilité.

**→ ARBITRÉ (suite)** : l'atelier a publié ARBITRAGE_CREATION_ETUDE.md
(2026-10-27, validé par David) — la variante (b) est actée : dossier
non vide autorisé avec confirmation, refus dur si etude.json (ouverture
proposée), rien d'écrasé. Livré ci-dessous.

---

## SESSION 2026-10-27 (correctif création d'étude — P14.3)

Rituel de synchro : **ARBITRAGE_CREATION_ETUDE.md** (nouveau),
**INDEX_SPECS.md** (v3) et **FEUILLE_DE_ROUTE_V2** (2026-10-27c)
recopiés dans `architecture/spec_v2/`. INDEX : P15 clos, P16 livré,
correctif création d'étude avant la recette P16 et P17.

### Correctif appliqué (ARBITRAGE_CREATION_ETUDE, 4 points)

1. **Dossier non vide autorisé** (`services/etude_io.creer_etude`) —
   la règle « vide ou inexistant » est retirée du service ; la
   confirmation est portée par l'UI (dialogue « Nouvelle étude » :
   « Ce dossier contient déjà N élément(s). Créer l'étude ici quand
   même ? », avec rappel qu'aucun fichier existant ne sera modifié
   ni supprimé).
2. **Refus dur si etude.json présent** : message « contient déjà une
   étude ; elle ne s'écrase pas — ouvrez l'étude existante ou
   saisissez un nom de nouveau dossier » ; l'UI propose l'ouverture
   de l'étude existante (Oui → ouvrir, Non → rien).
3. **Rien d'écrasé** : la création n'écrit que etude.json et les
   sous-dossiers de l'étude ; les conflits de nom (un fichier
   existant nommé reunions/blocs/traitements/synthese/parametres
   ou dans leurs sous-chemins) sont détectés **avant toute
   écriture** — erreur claire, dossier laissé intact.
4. **Aide dans les messages d'erreur** : « Saisissez plutôt un nom
   de nouveau dossier pour créer l'étude dedans. »

Contrat format étude inchangé (§2 : structure du dossier, pas la
vacuité préalable) ; règle non-destructif toujours couverte par
tests. 3 tests unitaires : création dans dossier non vide OK (fichiers
existants intacts), refus déjà-étude (étude existante intacte),
refus conflit de nom (rien d'écrit). **194 tests verts.**

Note : la confirmation UI elle-même (QMessageBox) n'est pas couverte
par test automatisé — comportement modal à vérifier à la main à la
prochaine utilisation.

---

## SESSION 2026-10-27 (P17) — RÉSUMÉ + SYNTHÈSE D'ÉTUDE : LIVRÉ

INDEX_SPECS v3 : « correctif création d'étude, puis validation P16
(recette) et P17 ». Le correctif est livré (ci-dessus) ; P17 est
livré ci-dessous ; la **recette P16** nécessite la clé API et le
jugement humain de David — checklist en fin de session. **228 tests
verts** (194 + 34 nouveaux : 30 services + 4 UI).

### P17.1 — Bloc Résumé ⭐ TERMINÉ

`services/traitements/resume.py` (ServiceResume) + `ui/resume_window.py`
(bouton « Résumé… » de la page Étude, QDialog modal) :

- **source au choix à chaque lancement** : reformulations validées
  (défaut, paramétrable) ou transcription brute corrigée (blocs actifs
  de la segmentation) ; erreur claire si aucune reformulation
  validée ; **la source est stockée avec le résultat** (contrat §8) ;
- **avertissement source évoluée** : reformulation validée
  postérieure (source reformulée) ou projet v1 modifié (source
  brute) → signalé dans la fenêtre, jamais de mise à jour
  automatique ;
- **longueur cible paramétrable au lancement** (défaut 650-700,
  éditable dans les paramètres de l'étude) ;
- **segmentation déterministe** : source > 24 000 tokens → 3 à 5
  segments coupés aux frontières de paragraphes avec léger
  chevauchement (2 paragraphes) ; notes de segment (extraction dense)
  puis **assemblage final par le LLM** (le résumé final n'est jamais
  un collage de mini-résumés — prompt v2 §« ne pas suivre la
  structure des interventions ») ; source courte en un seul appel ;
- estimation de coût avant lancement (affichée puis confirmée) ;
- outillage commun du moteur : relance complète avec consigne
  (contexte = source + formulation courante + **toutes** les
  versions antérieures), relance ciblée sur sélection (contexte
  identique + versions antérieures, le reste conservé tel quel),
  édition manuelle = nouvelle version `edition_manuelle`,
  validation fige le résumé (`resume_valide`), dévalidation,
  retour arrière avec navigation d'historique ;
- stats cumulées des appels stockées par version (champ additionnel
  `stats` + `origine` sur VersionResume, toléré par le schéma —
  même approche que `chemin_absolu`/`buffer` en P14).

### P17.2 — Synthèse d'étude ⭐ TERMINÉ

`services/traitements/synthese.py` (ServiceSynthese) + page Étude :

- source = textes validés des réunions dans l'ordre de l'étude
  (**résumé validé prioritaire** — plus compact — sinon
  reformulations validées) ; troncation par le haut au-delà de
  80 000 tokens d'entrée (les réunions les plus récentes restent) ;
- **mise à jour automatique quand une réunion devient entièrement
  validée** (tous ses blocs actifs validés — hook dans
  ReformulationWindow.valider_bloc, génération en arrière-plan,
  barre d'état) + **régénération manuelle** depuis la page Étude
  avec estimation ; versionnée (contrat §9), exactement une entrée
  de journal par opération (stats en entrée) ;
- **cases de contexte** (feuille de route §3.1 « blocs qui le
  cochent ») : `contexte.fenetre_glissante` et
  `contexte.synthese_etude` dans les paramètres reformulation de
  l'étude — cochées par défaut, absentes d'une étude antérieure =
  actives (rétrocompatible), moteur et estimation respectent le
  décochage, cases affichées dans Paramètres de l'étude ;
- prompt synthèse = constante intégrée (`PROMPT_SYNTHESE`,
  rubriques : thème, pensées développées, versets cités,
  vocabulaire récurrent — contrat §10 ne prévoit pas de prompt
  éditable pour la synthèse).

### P17.3 — Contrôle qualité étendu ⭐ TERMINÉ

`services.controle_qualite.expressions_recurrentes` + bouton
« Récurrences… » de la page Étude : n-grammes de 3 à 6 mots
normalisés sur les textes validés (reformulations + résumés),
signalés à partir de 3 occurrences dans au moins 2 réunions (le
filtre sur les réunions concentre le rapport sur les tics de
reformulation, pas sur le vocabulaire du thème) — gratuit, sans
LLM, liste indicative triée, jamais de remplacement suggéré.

### Bilan tests : **228 verts** (194 + 34)

test_resume_synthese.py (30) : sources, segmentation bornée 3-5,
génération mono et multi-segments avec stats cumulées, persistance
disque, estimation, relances (versions antérieures + sélection),
édition/validation/dévalidation, échec appel = aucune version
écrite, source évoluée, réunion entièrement validée, résumé
prioritaire dans la synthèse, ordre + troncation, journal une
entrée, cases de contexte (3), récurrences (3).
test_resume_ui.py (4) : résumé éditable non validé, édition =
nouvelle version, validation fige, dévalidation rouvre.

### DÉCISIONS / ÉCARTS DE LA SESSION (P17) — à arbitrer par l'atelier

1. **Synthèse automatique au moment où la réunion devient
   entièrement validée**, pas « à chaque validation de bloc »
   (contrat §9) : un appel LLM à chaque clic de validation serait
   lent et coûteux ; la version « dernier bloc validé » réalise
   l'intention du contrat (déclencheur `validation_bloc`) sans le
   bruit. Arbitrage bienvenu si l'atelier voit autrement.
2. **Assemblage du résumé segmenté par LLM** (notes de segments →
   passe finale) : la feuille de route dit « segments puis
   assemblage » sans préciser le mode ; le collage direct
   dupliquerait les chevauchements, d'où la passe finale.
3. **Champs additionnels `stats`/`origine` sur les versions de
   résumé** (contrat §8 ne les montrait pas) : l'indicateur de
   version de l'UI en a besoin (même logique que §7).
4. **Avertissement source brute approximatif** : comparaison mtime
   du `project.sttproj` (les horodatages internes v1 ne changent pas
   à chaque correction) ; horodatages à la seconde — une correction
   dans la même seconde que la génération n'est pas détectée.
5. **Fenêtre Résumé modale** (QDialog) quand la page Reformulation
   est non modale : un résumé par réunion, pas de table.
6. **Bouton « Résumé… » disponible même sans reformulation** : la
   source brute corrigée suffit (vue d'ensemble rapide — feuille de
   route §4).

### RECETTE P16 (à faire par David — clé API + jugement humain)

Prérequis : réglages LLM (fournisseur + clé « Tester la clé »),
étude avec Luc 01b référencée, segmentation générée (page Étude).

1. Page Étude → « Reformulation… » → « Traiter les blocs non
   validés » : le coût estimé s'affiche avant la première passe
   (B1) ; vérifier le traitement séquentiel et l'affichage du coût
   réel en fin de passe.
2. Relire chaque résultat face à sa source (fidélité stricte,
   références complétées, « nous » de foi conservé — prompt v2).
3. Régénérer un bloc avec une consigne libre (« plus concis… ») ;
   retravailler une sélection dans un autre bloc.
4. Éditer un bloc à la main → sauvegarder (nouvelle version) →
   valider ; vérifier qu'un bloc validé est figé et que la
   dévalidation rouvre l'édition.
5. Dévalider un bloc, le re-traiter : seuls les blocs suivants non
   validés sont retraités, aucune cascade.
6. Annuler une passe en cours : tout ce qui est produit est
   conservé, la reprise saute les blocs traités.
7. Sur une méditation longue (monologue) : vérifier les jonctions
   entre sous-blocs (pas de rupture stylistique perceptible).
8. Valider tous les blocs → la synthèse d'étude se met à jour
   automatiquement (barre d'état + page Étude).
9. « Résumé… » : générer depuis les reformulations validées, puis
   valider ; régénérer la synthèse ; bouton « Récurrences… ».
10. Jugement humain P17 : résumer une 2ᵉ réunion (Luc 01a) et
    vérifier qu'elle « sait » ce que la 1ʳᵉ a développé (rappels
    redondants absents) — critère d'acceptation de la feuille de
    route.

---

## SESSION 2026-10-27 (correctifs post-P17, retour utilisateur)

### 1. Crash « Reformulation » sur une réunion sans segmentation ⭐ CORRIGÉ

- **Constat** (David) : `DecoupageError: Aucun découpage pour la
  réunion 2026-09-24_..._luc01a` au lancement de la page
  Reformulation. **Origine** : la génération du découpage (P14.4,
  `generer_decoupage`) n'était exposée **nulle part dans l'UI** —
  service complet et testé, mais aucun bouton ne le déclenchait :
  la segmentation n'était jamais produite pour une réunion réelle.
- **Correctif** : `_assurer_decoupage` dans la page Étude — à
  l'ouverture de « Reformulation littéraire… » ou « Résumé… », si
  la réunion n'a pas de segmentation, l'UI propose de la générer
  maintenant depuis la diarisation validée du projet v1
  (confirmation, projet v1 non modifié) ; avertissement explicite
  si le projet ne comporte aucun bloc de parole (diarisation à
  valider d'abord dans l'éditeur de transcription) ; erreurs du
  service affichées proprement, plus jamais de traceback.

### 2. Libellés des boutons de la page Étude ⭐ CORRIGÉ

- « Ouvrir dans l'éditeur » → **« Correction de transcription… »**
  (tooltip : éditeur v1, étape de correction de l'oral) ;
- « Reformulation… » → **« Reformulation littéraire… »** (tooltip :
  page de relecture, blocs éditables, validation) ;
- « Résumé… » conservé, tooltip précisé ; tooltip de la liste des
  réunions (le double-clic ouvre la correction de transcription).

### 3. Accueil : bouton « Ouvrir l'étude sélectionnée » ⭐ AJOUTÉ

La liste des études récentes s'ouvre au double-clic ; ajout d'un
bouton explicite « Ouvrir l'étude sélectionnée » (lancement des
traitements sans connaître le double-clic) + tooltip de la liste.

### Bilan : 228 tests verts (aucun impact service — correctifs UI)

---

## SESSION 2026-10-27 (P16-bis) — CORRECTIFS DE RELECTURE UI : LIVRÉ

Rituel de synchro (skill v15) : INDEX_SPECS.md (v du jour),
UI_REFORMULATION_MODIFS_V2_2026-10-27.md (nouveau — prime sur
UI_REFORMULATION_V2 pour ses points), UI_REFORMULATION_V2
(2026-10-27b) et FEUILLE_DE_ROUTE_V2 (2026-10-27d) recopiés dans
`architecture/spec_v2/` ; PROJECT_STATE.md remonté vers le dossier
Synchro du Drive.

### Correctifs appliqués (spec UI_REFORMULATION_MODIFS §1-§5)

1. **Défilement unique synchronisé** : la table de relecture est
   désormais un `QTableWidget` — une seule barre de défilement
   vertical pour toute la page (les deux colonnes défilent
   ensemble) ; **aucune barre de défilement dans une cellule** :
   les cellules sont des `QTextEdit` dont la hauteur de contenu
   est exacte (le `documentSize()` de `QPlainTextEdit` sous-estime
   la hauteur — layout propre, constaté par sonde), barres
   désactivées, retour à la ligne sur la largeur de colonne ;
   hauteur de ligne = max des deux cellules (l'autre se cale en
   haut), maintenue au fil de la frappe (`documentSizeChanged`)
   et au redimensionnement des colonnes.
2. **Colonne locuteurs = noms par bloc** : colonne 0 de la table,
   une cellule par ligne (« / » pour un bloc fusionné
   multi-locuteurs) ; le panneau de cases à cocher est retiré ;
   l'API de filtrage est **conservée** (`selectionner_locuteur`,
   `appliquer_filtrage`, `ligne_visible` — lignes masquées de la
   table), prête à rebrancher sur un menu « Filtrer par
   locuteur… » (non implémenté, conformément à la spec §2.3).
3. **Zone gauche de la timeline = largeur de la colonne
   locuteurs** : le panneau des locuteurs de la timeline suit la
   colonne 0 (`sectionResized`), bord gauche aligné.
4. **Bouton « Reformulation… » dans l'éditeur v1** : actif si le
   projet appartient à une étude, sinon désactivé avec l'info-bulle
   « Ce projet n'appartient à aucune étude » ; ouvre la page
   Reformulation de la réunion courante (brique inverse du lien
   « Correction de transcription… » de la page Étude) ;
   segmentation assurée par la fonction partagée
   `assurer_decoupage` (extraite de la page Étude) ; projet
   référencé par plusieurs études → dialogue de choix.
5. **Persistance de la taille de police** : A+/A− mémorisé dans
   les réglages (`SettingsManager.get/set_reformulation_prefs`),
   réappliqué à chaque ouverture ; **défaut abaissé à 11** (double
   colonne — à vérifier en relecture par David, spec §5.2) ; plage
   9-24 inchangée ; **largeurs de colonnes mémorisées** aussi
   (locuteurs, texte brut, pastilles ; enregistrées à la
   fermeture, la taille de police à chaque changement).

### Correctif création d'étude (ARBITRAGE_CREATION_ETUDE)

Déjà livré (commit 6b4c564, 3 tests) ; complément : test de
l'aide « Saisissez plutôt un nom de nouveau dossier » dans les
deux messages d'erreur (point 4 de l'arbitrage).

### Décisions / écarts de la session (P16-bis)

1. **Recherche des études du projet** : parmi les **études
   récentes** des réglages (aucun registre global des études
   n'existe) — une étude jamais ouverte sur cette machine ne sera
   pas trouvée ; à arbitrer si l'atelier veut un scan disque.
2. **Bouton désactivé plutôt que masqué** (spec §4.2 laisse le
   choix) : la fonctionnalité reste visible et expliquée par
   l'info-bulle.
3. **Colonne reformulée en Stretch** (absorbe l'espace restant) :
   seules les largeurs locuteurs/brute/pastilles sont mémorisées
   ; l'utilisateur redimensionne via l'en-tête (poignées).
4. **`QTextEdit` au lieu de `QPlainTextEdit`** pour les cellules :
   détail d'implémentation exigé par le calcul de hauteur exact
   (`documentSize` fiable), texte riche refusé
   (`setAcceptRichText(False)`), normalisation \n inchangée.
5. **Réglages injectables** : `MainWindow(settings=...)` et
   `ReformulationWindow(settings=...)` — les fumées ne touchent
   jamais la configuration réelle (leçon des études parasites
   P16) ; l'éditeur v1 transmet ses réglages à la page
   Reformulation ouverte depuis le bouton.
6. La règle 6 (§7) sur le filtrage reste testée via l'API
   conservée (plus de boutons dans l'UI).

### Bilan tests : **243 verts** (228 + 15)

`tests/unit/test_reformulation_ui.py` réécrit : 25 tests (11 de la
spec §7 adaptés + 14 nouveaux couvrant les **5 règles d'invariance
additionnelles §6** de la spec correctifs : aucune barre de
défilement dans une cellule [3 fumées offscreen], hauts des
cellules brute/reformulée alignés et hauteurs variables, largeur
de la zone gauche de la timeline = colonne locuteurs, persistance
taille police + largeurs après fermeture/réouverture + défaut
abaissé, bouton « Reformulation… » actif/inactif et réunion
exacte) ; `test_etude_format.py` : +1 (aide des messages).

---

## SESSION 2026-10-28 (P16-bis, 2ᵉ série + terminologie) : LIVRÉ

Rituel de synchro (skill v17) : INDEX_SPECS.md (terminologie
arbitrée), UI_REFORMULATION_MODIFS_V2_2026-10-27b.md et
UI_REFORMULATION_MODIFS_V2_2026-10-27c.md (1ʳᵉ + 2ᵉ série —
prime sur tout le reste pour ses points) recopiés dans
`architecture/spec_v2/`.

### 2ᵉ série (spec MODIFS §8-§12)

1. **Synchro bidirectionnelle timeline ↔ blocs (§8)** : clic
   sur un bloc (colonne brute, cellule locuteurs, pastille) =
   curseur au début du bloc + timeline défilée vers le segment
   (`set_current_time` → `ensure_cursor_visible`, zone de
   défilement branchée sur le composant v1) ; clic timeline =
   bloc courant sélectionné (`sur_clic_timeline`, marche en
   pause) ; lecture = bloc surligné + **défilement paresseux**
   (`_defiler_vers_bloc` : seulement quand le bloc courant
   sort de la zone visible, jamais si le focus clavier est
   dans la table).
2. **Surlignage lisible dans les deux thèmes (§9)** : couleurs
   centralisées dans `services/theme_manager`
   (`couleurs_surlignage` / `est_sombre`, résolution « system »
   par la palette) — clair : jaune #FFF3B0 inchangé ; sombre :
   ambre sombre #6B5300 (texte clair dessus, contraste AA ≥
   4,5 vérifié par test WCAG), bleu clair #64B5F6 pour le bloc
   joué ; plus aucune couleur de surlignage codée en dur dans
   la page. (Le composant v1 block_widget gérait déjà son
   jaune assombri en sombre.)
3. **Timeline : gouttière et bord droit (§10)** : la gouttière
   gauche (panneau locuteurs) est **hors** de la zone
   défilante, exactement à la largeur de la colonne locuteurs ;
   seule la timeline défile ; `update_timeline_width` borne la
   largeur par le viewport (pistes jusqu'au bord droit, plus
   de marge vide) — réétalé au redimensionnement (eventFilter
   sur le viewport + resizeEvent).
4. **Navigation à pile unique (§11)** : nouvelle
   `ui/app_window.py` — **AppWindow**, unique fenêtre
   principale (QStackedWidget) : Accueil → Étude → Réunion
   (Correction / Reformulation), clés uniques par chemin
   résolu (une étude ou une réunion déjà ouverte est
   **réactivée**, jamais dupliquée) ; « Accueil » = toujours
   l'accueil de l'app ; bouton **« Retour à l'étude »**
   distinct sur les pages Réunion (éditeur v1 : visible si la
   réunion appartient à une étude ; page Reformulation :
   toujours) ; les pages sauvegardent leur état en sortie
   (`sur_navigation_sortante`) et à la fermeture de l'app ;
   point d'entrée `TranscriptStudio.py` passe à AppWindow.
   Les dialogues modaux (Résumé, Log, paramètres) restent des
   QDialog — pas des pages.
5. **« Ouvrir une étude depuis un dossier… » (§12)** : l'ancien
   bouton « Ouvrir une étude » (sélecteur de dossier) est
   renommé et **valide etude.json** — dossier sans étude :
   message clair, rien ne s'ouvre ; l'étude ouverte rejoint les
   études récentes (la liste des études récentes reste
   accessible par double-clic et « Ouvrir l'étude
   sélectionnée »).

### Terminologie « réunion » (§13, arbitrée David)

Renommage d'**affichage uniquement** (code, format de fichier,
specs et identifiants inchangés — « projet v1 » reste le terme
technique) : accueil (« Réunions récentes », « Nouvelle
réunion », « Ouvrir une réunion », « Réunion (*.sttproj) »),
éditeur v1 (tooltips, « Réunion modifiée », réparation,
messages), dialogues v1 (répertoires, réunion provisoire),
page Étude (filtres, relocalisation, messages), éditeur v1
filtres de fichiers. Revue systématique faite sur tous les
libellés des `ui/*.py` ; le manuel utilisateur PDF n'est pas
régénéré (reporté à la livraison visible, comme convenu en
P16).

### Décisions / écarts de la session (2ᵉ série)

1. **« Retour à l'étude » de l'éditeur v1** : si la réunion
   appartient à plusieurs études, revient à la plus récente
   (même choix que le bouton « Reformulation… », qui lui
   propose le dialogue de choix) — arbitrage bienvenu.
2. **AppWindow** remplace les fenêtres séparées de P14.3 ;
   les pages restent constructibles autonomes (tests,
   lancement direct) avec repli sur l'ancien comportement
   quand aucun `navigation` n'est injecté.
3. **Contraste AA vérifié par test** avec la formule WCAG
   (luminance relative + rapport 4,5:1 texte, 3:1 bord de
   bloc) ; la relecture visuelle des deux thèmes reste à
   David (offscreen = palette claire).
4. **« Ouvrir une étude » → « Ouvrir depuis un dossier… »** :
   la spec §12 décrit le nouveau bouton « à côté de
   Ouvrir une étude » ; le bouton existant faisait déjà ce
   travail (sélecteur de dossier) — renommé + validateur
   ajouté plutôt que deux boutons redondants.
5. Le surlignage du **mot lu** de la page Reformulation
   suivait le thème via la palette à chaque appel (changement
   de thème pris en compte sans rechargement).

### Bilan tests : **261 verts** (243 + 18)

`tests/unit/test_p16bis_serie2.py` (18) : **règles §14**
complètes — aller-retour bloc ↔ timeline (clic bloc = curseur
au début ; clic timeline = bloc courant sélectionné), bloc
courant surligné et ramené dans la zone visible sans
intervention (40 blocs) + jamais de défilement pendant
l'édition ni si déjà visible, couleurs par thème + contraste
AA (formule WCAG) + aucun jaune clair partagé + couleur du
mot lu passée par la fenêtre, gouttière = colonne locuteurs +
pistes ≥ viewport (bord droit), pile unique (pas de doublons,
Accueil = accueil, Retour à l'étude depuis la reformulation et
l'éditeur), dossier sans etude.json refusé proprement + étude
valide ouverte et mémorisée.

---

## SESSION 2026-10-28 (P16-bis, 3ᵉ série) : LIVRÉ

Rituel de synchro (skill v18) : INDEX_SPECS.md et
UI_REFORMULATION_MODIFS_V2_2026-10-27d.md recopiés dans
`architecture/spec_v2/` (§1-14 inchangés par rapport à la
version c — vérifié par diff ; seule la 3ᵉ série §15-18 est
nouvelle).

### Correctifs appliqués (spec MODIFS §15-§18)

1. **Lecteur audio sain au retour (§15)** : quitter la page
   Reformulation (Étude/Accueil, pile unique) **arrête la
   lecture et libère l'audio** (`_quitter_page` : stop +
   unload + bouton réinitialisé, dernière position
   conservée) ; le retour réinitialise un lecteur **jouable
   immédiatement** (`sur_navigation_entrante`, appelé par
   AppWindow à l'activation de la page : rechargement du
   fichier, curseur restauré à la dernière position) ;
   erreur du périphérique **signalée dans la barre d'état**
   (nouveau signal `PlaybackManager.erreur_audio`, jamais
   d'échec silencieux) — cause de l'état zombie : le lecteur
   était déchargé en quittant la page mais jamais rechargé
   au retour.
2. **Aucune lecture automatique au clic (§16)** : le clic
   (bloc, cellule locuteurs, pastille, timeline) **positionne
   et sélectionne sans jamais jouer** — `positionner_audio`
   ne lance plus la lecture (le lancement résiduel
   `jouer_audio_si_charge` est retiré du chemin de clic,
   méthode réduite à un garde-fou inactif) ; **seul le bouton
   lecture/pause joue**.
3. **Clé API LLM persistée (§17)** — DEUX causes
   racine, la seconde constatée en relecture par
   David (capture : clé saisie + test OK, puis
   disparue après enregistrement) :
   - (a) `CredentialStore._load_credentials` ne
     rechargeait que la clé ElevenLabs — les clés
     `llm_cle_*` étaient écrites mais perdues au
     redémarrage (corrigé au commit précédent) ;
   - (b) **`SettingsManager.save()` réécrit
     settings.json EN ENTIER** (dictionnaire qui ne
     connaît pas les clés `llm_cle_*`) : chaque
     sauvegarde de réglages — enregistrement des
     paramètres, changement de thème, projet/étude
     récent — EFFAÇAIT les clés du fichier, juste
     après que le CredentialStore les y avait
     écrites. Correctif à la racine : les
     credentials vivent désormais dans leur
     **propre fichier `credentials.json`** (dossier
     de paramétrage), avec **migration automatique**
     à la première exécution (clé ElevenLabs P6 +
     clés LLM P15 relues depuis settings.json) ;
     plus aucune écriture de credential dans
     settings.json, plus aucun effacement possible.
     L'UX est inchangée et à parité ElevenLabs
     (champ masqué prérempli, « Tester la clé »
     sans ressaisie, vider le champ = effacer).
     Deux tests de régression : survie à
     set_theme/add_recent_project/set_llm_config
     puis relecture, et scénario complet saisie →
     enregistrement → réouverture (champ toujours
     prérempli).
4. **Éditeur de catalogue lié à la sélection (§18)** :
   les incohérences constatées venaient d'écritures
   transitoires pendant les rechargements (les champs
   écrivent en direct dans les objets ; en changeant de
   fournisseur, les valeurs de l'ancien fournisseur
   s'écrivaient un instant dans le nouveau). Corrigé :
   rechargements sous garde `_remplissage` (signaux
   ignorés), **changement de fournisseur = désélection de
   tout modèle** (panneau à l'état par défaut), panneau
   d'édition strictement lié au modèle sélectionné du
   fournisseur courant (id introuvable → panneau vidé),
   **identifiant en doublon refusé avec message** au moment
   de la frappe (retour à l'identifiant précédent), défauts
   embarqués préremplis et « Réinitialiser » inchangé, et
   **repli sur le catalogue embarqué si le fichier stocké
   est invalide** (doublons d'une version antérieure —
   fichier conservé, réparable par « Réinitialiser les
   valeurs par défaut ») — sans ce repli, un catalogue
   corrompu bloquait l'ouverture des réglages.

### Retour relecture David (compléments §17 + accueil)

1. **Statut de test conservé par fournisseur** : le
   résultat de « Tester la clé » (« Clé valide. » /
   « Clé invalide. », avec sa couleur) est mémorisé
   par fournisseur dans le dialogue ET **persisté
   dans le CredentialStore** (credentials.json) —
   changer de fournisseur et revenir ne repart
   plus de « Non testée. », et **la réouverture des
   réglages restaure le dernier résultat**. Garde-
   fou anti-staleness : le statut est **invalidé si
   la clé change** (il concernait l'ancienne clé) ;
   la même clé réenregistrée (aller-retour de
   fournisseur, enregistrement des réglages) le
   conserve. Le texte du statut ne contient
   jamais la clé.
2. **Accueil — état du service de reformulation** :
   nouvelle ligne sous l'état de transcription,
   « Service de reformulation : configuré — <noms
   des fournisseurs dont la clé est enregistrée
   (ou fournisseurs locaux sans clé)> » / « non
   configuré » ; rafraîchie après fermeture des
   réglages. 4 tests (statut conservé par
   fournisseur, statut survit à la réouverture,
   invalidation par changement de clé, ligne
   d'accueil).

### Décisions / écarts de la session (3ᵉ série)

1. `SettingsDialog(settings=...)` accepte des réglages
   injectables (même approche que les autres fenêtres —
   les fumées n'écrivent jamais dans la config réelle).
2. La clé masquée préremplie reste la clé réelle dans un
   champ `Password` (même mécanique que l'onglet ElevenLabs
   historique — parité stricte plutôt que placeholder).
3. Le repli sur les défauts en cas de catalogue stocké
   invalide ne répare pas le fichier automatiquement
   (choix conservateur : l'utilisateur peut encore le
   récupérer via « Réinitialiser », rien n'est écrasé).

### Bilan tests : **283 verts** (261 + 22)

`tests/unit/test_p16bis_serie3.py` (22) : arrêt/libération
au quit + position conservée puis restaurée + erreur
signalée + `sur_navigation_entrante` appelé par la pile au
retour ; aucun chemin de clic ne joue (bloc, timeline,
bloc timeline) + seul le bouton bascule ; clé LLM qui
survit à un « redémarrage » (nouveau CredentialStore sur
le même fichier) + champ masqué prérempli + vider =
effacer ; catalogue — chaque fournisseur n'affiche que ses
modèles, changement de fournisseur désélectionne, panneau
= modèle du fournisseur courant, aucune liste sans
doublon, défauts non corrompus après un parcours complet,
identifiant en doublon refusé avec message, fichier
stocké invalide → repli sur les défauts embarqués.

### P17 vérifié intégré après P16-bis (2026-10-28)

P17 était livré AVANT la refonte P16-bis (page
Reformulation réécrite, assurer_decoupage extrait
en fonction partagée, navigation à pile unique) :
3 fumées d'intégration nouvelles
(`tests/unit/test_p17_integration.py`) prouvent que
le câblage tient — chaque validation de bloc
appelle le déclencheur de synthèse (validation_bloc,
contrat §9) et la condition « réunion entièrement
validée » ne devient vraie qu'au dernier bloc ;
« Résumé… » ouvre la fenêtre de LA réunion
sélectionnée avec segmentation assurée par la
fonction partagée ; « Récurrences… » produit son
rapport. **Reste la recette humaine de P17** (clé
API réelle + jugement de David — checklist en fin
de session P17 ci-dessous) ; P18 ensuite.

## SESSION 2026-10-28 (P18) — JND LOCALE, RÉFÉRENCES & EXPORT : LIVRÉ

Rituel de synchro : dossier Drive inchangé depuis le skill v18
(INDEX_SPECS et MODIFS 27d déjà recopiés ; PROJECT_STATE distant
= mes propres montées, aucune annotation atelier) — la spec P18
est la feuille de route §5.2, §5.4, §6, §7.

### P18.1 — Ressource JND (services/jnd.py)

- Chargeur **OSIS XML avec espace de noms** (tags locaux), texte
  des versets hors `<note>` ; une entrée par verset, indexée
  livre/chapitre/verset (formats osisID « Gen 1.1 » et « Gen.1.1 »).
- **Table des 66 livres** français (noms canoniques + abréviations
  courantes, Jn/Lc/Ps/1S/És...), correspondance **insensible à la
  casse et aux accents**.
- **Parsing des références du texte libre** : « Luc 15.11-32 »,
  « Jn 3:16 », « genèse 2 verset 4 à 6 », « Ps 23 », « 1 Samuel 3 »,
  plages avec -/à/et ; un nom de livre sans chapitre n'est PAS une
  référence (pas de faux positifs « job », « actes ») ;
  normalisation canonique « Genèse 2.4-6 ».
- Lookup ponctuel / plage / chapitre entier, recherche par
  expression. Fichier **non distribué** :
  `resources/bible/JND.osis.xml` (LISEZ-MOI + section README
  « Installation de la Bible JND », comme FFmpeg) ; `BibleAbsente`
  = erreur claire, l'app fonctionne sans.

### P18.2 — Contrôle qualité références et citations (§5.2/§5.4)

- Références **complétées** par le résultat = SUGGESTION de
  validation avec **extrait JND** : nouveau passage, ou
  **complétion de numéros de versets** (« Luc 15 » -> « Luc 15.11 » :
  les numéros ont été ajoutés, la vérification se justifie) ;
  jamais une alerte (la complétion est voulue).
- Références de la source **absentes du résultat** = alerte
  discrète (comptées dans nb_alertes).
- **Citations** entre guillemets associées à une référence proche
  (~160 caractères) : « exacte » ou « écart » (paraphrase) selon la
  comparaison normalisée au texte JND.
- **« Aligner les citations sur la JND… »** au menu de la pastille
  (bloc non validé) : remplace les citations en écart par le texte
  JND — À LA DEMANDE, jamais automatique ; c'est une édition
  ordinaire (une nouvelle version est créée à la sauvegarde,
  indicateur non enregistré).
- Sans la Bible installée : parsing et comparaisons locales
  toujours actifs (gratuits), sans extraits ; message pointer vers
  le README.
- L'indicateur de la page Reformulation (survol de la pastille)
  affiche désormais longueur + interdits + références.

### P18.3 — Export de l'ouvrage (services/export_ouvrage.py)

- **Assemblage** : par réunion dans l'ordre de l'étude — résumé
  validé en tête de section (si coché), puis reformulations
  validées dans l'**ordre d'ouvrage** ; réunions sans texte validé
  exclues ; réunion sans découpage ignorée proprement.
- **DOCX** (python-docx, déjà en dépendance) : styles sobres,
  guillemets “...” (les « » du texte validé sont convertis),
  **pas de gras dans le corps** (les titres sont des styles de
  structure), titres de réunion optionnels (titre 1 de la réunion
  sinon son nom).
- **TXT** simple en complément (choix du format dans le dialogue
  de fichier).
- Bouton **« Exporter l'ouvrage… »** sur la page Étude : options
  (résumés, titres), fichier (dossier de l'étude par défaut),
  message de fin avec **Ouvrir le fichier / Ouvrir le dossier**
  (flux P13 réutilisé).

### Complément (retour David : Bible installée)

David a installé les deux éditions réelles (modules
CrossWire, 22 Mo chacun) : `resources/bible/Darby.osis.xml`
(JND classique, FreJND) et `DarbyR.osis.xml` (révisée,
FreBPC). Conséquences livrées :

- les modules réels utilisent des versets **milestone**
  (`<verse sID/> texte <verse eID/>`) — le chargeur
  initial (versets conteneurs) n'y voyait que des
  éléments vides ; réécriture en machine à états
  (les deux styles restent acceptés), notes et
  titres exclus du texte, espaces insécables
  nettoyées ; **vérifié sur le fichier réel : 31 167
  versets, 66 livres, lookups exacts** (Genèse 1.1,
  Luc 15.11-12, Jean 3.16, Psaume 23, recherche
  « brebis perdue » → Matthieu 10.6/15.24, Luc 15.6,
  contrôle références + citations + alignement bout
  en bout) ;
- noms acceptés par priorité : JND.osis.xml (explicite)
  > Darby.osis.xml (classique, la « JND » citée par
  les orateurs) > DarbyR.osis.xml ; README et LISEZ-MOI
  mis à jour — **arbitrage atelier bienvenu** sur
  l'édition de référence pour le contrôle qualité ;
- limite connue : l'alignement d'une citation en écart
  insère le texte entier du verset, préfixe narratif
  inclus (« Et il dit : Un homme avait deux fils ; »
  pour Luc 15.11) — c'est une édition à relire (jamais
  automatique), l'utilisateur ajuste ; affiner au
  besoin en P19+.

### Décisions / écarts de la session (P18)

1. **P18.4 pré-correction NON réalisée** : optionnelle dans la
   feuille de route ; le dictionnaire biblique attendu
   s'appuierait sur services/jnd — arbitrage atelier bienvenu.
2. **Manuel utilisateur PDF non régénéré** (report de la section
   Études déjà acté ; la mise à jour du manuel arrive avec la
   livraison visible P19/P20) — README couvre la ressource JND.
3. La complétion de **numéros de versets** est signalée comme
   suggestion (pas seulement les références entièrement
   nouvelles) : les numéros ont été inventés par le LLM, la
   vérification JND se justifie ; à faire valider par l'atelier.
4. `resources/bible/` + LISEZ-MOI ajoutés au dépôt (le fichier
   OSIS lui-même reste non suivi, hors périmètre Git comme FFmpeg).

### Bilan tests : **312 verts** (286 + 26)

`tests/unit/test_p18.py` (26) : Bible absente (erreur claire),
chargeur avec espace de noms + exclusion des notes, lookup
ponctuel/plage/chapitre, référence introuvable, parsing des
variantes françaises + pas de faux positifs, normalisation,
recherche, suggestion avec extrait, complétion de versets
signalée, référence perdue, contrôle sans Bible (parsing local,
message README), controles_bloc complet, citation exacte vs
écart (paraphrase), alignement à la demande (paraphrase remplacée
une fois, citation exacte intacte), assemblage selon l'ordre
d'ouvrage + exclusion d'une réunion vide + options, DOCX relu
(ordre résumé→bloc 2→bloc 1, pas de gras dans le corps), TXT
(ordre), guillemets “...” dans le DOCX.

---

## SESSION 2026-10-28 (P18.5) — TÉLÉCHARGEUR DE BIBLES & VERSION RETENUE PAR ÉTUDE : LIVRÉ

Rituel de synchro : INDEX_SPECS.md (skill v19/v20),
BIBLE_JND_V2_2026-10-28b.md (+ 28) et
FEUILLE_DE_ROUTE_V2_2026-10-28b.md recopiés depuis le
Drive dans `architecture/spec_v2/` (le suffixe daté le
plus loin dans l'alphabet prime) ; spec
BIBLE_JND_V2_2026-10-28b = **fait autorité**.

### Services (services/bibles.py, nouveau)

- Catalogue des 3 versions (spec §1) : `darby`
  (JND éd. 2024 rév 2.0, domaine public), `darbyR`
  (JND révisée éd. 2026 rév 2.3, CC BY NC ND) —
  zips OSIS sur concordance.bible (miroir BPC, URLs
  vérifiées par recherche web) — et `segond1910`
  (domaine public, AUCUN lien direct vérifié →
  import manuel, ErreurBible invitant à
  « Charger depuis un fichier… »).
- Dossier de stockage `resources/bible/` **injectable
  pour les tests** ; fichiers **jamais commités**
  (règle 1, .gitignore).
- **Téléchargement** : zip en `.part`, extraction du
  premier .osis.xml, validation minimale, installation
  atomique, progression(lus, total) + annulation()
  callbacks ; échec/annulation = **aucun partiel
  conservé** (règle 4), zip supprimé aussi en cas de
  succès.
- **Import manuel** `installer_fichier` : validation
  minimale (OSIS lisible, ≥1 verset) puis copie
  atomique ; non-OSIS et OSIS vide refusés.
- **Version retenue par étude** (§3) :
  `version_bible_etude` (défaut **darbyR**, id inconnu
  → défaut, jamais bloquant), `bible_de_l_etude`
  (le contrôle qualité travaille TOUJOURS contre la
  version de l'étude — règle 3),
  `autres_versions_installees` (consultation des
  écarts de versification).

### Format étude

- `models/etude.py` : `ParametresEtude.bible`
  (dict, jamais requis) ; `parametres_par_defaut`
  écrit `{"version": "darbyR"}` ; **aucune migration**
  des études existantes (règle 2 : absence de bloc =
  défaut, testé y compris fichier non réécrit) ;
  validation schéma optionnelle (dict, version str).

### UI

- **Réglages, onglet « Bibles »** (spec §2) : une
  carte par version (nom, éditeur, édition, licence,
  état installée), « Télécharger » (QThread +
  QProgressDialog, annulation, remplacement confirmé,
  **jamais silencieux**), « Charger depuis un
  fichier… » ; Segond 1910 sans bouton Télécharger.
- **Paramètres de l'étude** : déroulant « Bible de
  référence » (état installé affiché), sauvegarde
  dans `bible.version` ; version non installée →
  message proposant d'ouvrir les réglages.
- **Page Reformulation** : `_bible_jnd` charge la
  Bible **de l'étude** ; l'indicateur de la pastille
  consulte les autres versions installées pour un
  écart de versification.
- **Page Étude / export** : la version retenue est
  affichée près de la synthèse et mentionnée dans
  l'export (« Bible de référence : <nom> », DOCX et
  TXT — spec §4.4).

### Versifications (§4)

`controle_references`/`controle_citations` acceptent
`autres_versions` : une référence (ou citation)
introuvable dans la version retenue devient une
**information** « autre versification ? » avec
l'extrait trouvé dans les autres versions installées —
consultation seulement, **jamais de décision
automatique**.

### jnd.py

Le repli implicite `chemin_bible()` garde
JND.osis.xml explicite en tête, puis **DarbyR (nouveau
défaut)** avant Darby — l'app passe partout par
bibles.py et la version de l'étude ; MESSAGE_BIBLE_ABSENTE
pointe vers l'onglet « Bibles » des réglages.

### Décisions / écarts de la session (P18.5)

1. Segond 1910 : aucun URL direct vérifié (404 sur les
   patterns essayés) → import manuel, message invitant
   à concordance.bible — conforme à la spec.
2. `Non confirmé 442609.crdownload` (résidu de
   téléchargement de David) : le fichier a disparu du
   dossier, rien à nettoyer.
3. Le message de la régle 5 (changement de version) ne
   touche ni reformulations, ni résumés, ni journal —
   testé au niveau données (aucune écriture autre que
   parametres.json).

### Bilan tests : **334 verts** (312 + 22)

`tests/unit/test_p18_5.py` (22) : les 5 règles
d'invariance §5 (git check-ignore + aucun .osis.xml
dans une étude ; étude sans bloc bible rouverte sans
migration ; contrôle contre la version retenue ;
annulation/panne réseau/zip sans OSIS = dossier vide ;
changement de version sans re-traitement), défaut
darbyR + id inconnu, schéma avec/sans bloc, écart de
versification (référence ET citation : information
avec extrait de l'autre version, honnête sans les
autres versions), téléchargement nominal file://,
Segond 1910 import manuel, import refusé (non-OSIS,
OSIS vide) / accepté, onglet Bibles des réglages,
déroulant des paramètres d'étude.

---

## SESSION 2026-10-29 (correctif) — EFFORT DE RAISONNEMENT : LIVRÉ

Retour David : « l'effort de raisonnement n'est pas
mémorisé, il revient toujours à faible ; la liste
déroulante est tronquée, d'autres efforts sont
disponibles (très élevé, etc.) ».

Trois causes réelles trouvées et corrigées :

1. **La valeur n'était jamais restaurée à
   l'ouverture des réglages** : le combo repassait
   à sa première entrée (« Faible »), et
   « Enregistrer » écrasait alors l'ancienne
   valeur. Désormais `on_llm_modele_change`
   sélectionne la valeur mémorisée (une valeur
   inconnue du catalogue est ajoutée telle
   quelle, jamais perdue).
2. **Le réglage n'était JAMAIS transmis à l'API** :
   le moteur, le résumé et la synthèse
   construisaient `ParametresCompletion` sans
   `effort_raisonnement` (ni `max_tokens`) —
   l'effort mémorisé ne servait de nulle part.
   Désormais envoyé UNIQUEMENT si le modèle le
   déclare (mêmes règles que la température,
   décision C2) ; None = clé absente de la
   requête = défaut de l'API.
3. **Sauvegarde dépendante de la visibilité** :
   `save_settings` n'écrivait température/effort
   que si la ligne était visible — changer
   d'onglet avant « Enregistrer » perdait le
   réglage. Désormais basé sur les capacités du
   modèle courant, pas sur l'onglet actif.

Niveaux exposés (liste commune
`services/llm/client.py::EFFORTS_RAISONNEMENT`,
utilisée par l'UI et testée) : Minimal / Faible /
Moyen / Élevé / **Très élevé** (reasoning_effort
minimal, low, medium, high, xhigh), plus « Défaut
de l'API » (None) en première entrée ; le combo
s'ajuste à son contenu (AdjustToContents —
fini la liste tronquée).

Bilan tests : **341 verts** (334 + 7) — effort
envoyé/présent selon le modèle (client factice +
moteur), max_tokens transmis, niveaux exposés,
restauration à l'ouverture + préservation à
l'enregistrement + réouverture (UI offscreen),
« Défaut de l'API » = None.

---

## SESSION 2026-10-29 (P18.6) — REFONTE DE LA NAVIGATION : LIVRÉ

**Synchro atelier spec** (rituel) : 8 documents du 2026-10-29 recopiés dans
`architecture/spec_v2/` — SPEC_NAVIGATION_V2_2026-10-29b (fait autorité),
ARBITRAGE_EXCLUSIVITE_REUNIONS_2026-10-29, CONTRAT_FORMAT_ETUDE_V2_2026-10-29
(invariant 13.5 réécrit : une réunion ∈ 0 ou 1 étude), FEUILLE_DE_ROUTE_V2_2026-10-29
(phase P18.6a-f insérée avant P19/P20), INDEX_SPECS_2026-10-29c, versions
intermédiaires conservées conformément au rituel. PROJECT_STATE.md copié vers
le dossier Drive Synchro (montée + hook post-commit).

### Ce qui a été livré (P18.6a à P18.6f, un commit par étape)

- **P18.6a — Hub** : trois tuiles (« Nouvelle transcription » / « Reprendre
  une réunion » / « Études »), bandeau app réservé à l'accueil (objectName
  `bandeau_app`, invariant §9.2 testable), salutation « Bonjour », dernières
  réunions en une colonne de mini-tuiles (titre, étude ou « Réunion autonome »
  + lien « rattacher à une étude… », stepper complet ①→⑥ conservé —
  réunions autonomes, coût). Fondations : `services/avancement.py` (états
  gris/bleu/vert des 6 étapes, `ETAPES_ETUDE` sans ⑥, ④⑤ optionnelles,
  `cout_reunion`), `ui/stepper.py` (StepperBar réutilisable, optionnelles en
  contour pointillé), trace d'export de réunion dans les réglages
  (`exports_reunions`, jamais dans le projet v1), `services/rattachement.py`
  (lecture légère des réunions d'une étude, `rattachement_de`,
  `verifier_exclusivite`, `rattacher`, `detacher_reunion`, `changer_etude`),
  `ui/rattachement_dialog.py`.
- **P18.6b — Page Réunion** (`ui/reunion_window.py`) : ruban (titre configurable
  via `titre_1`, date · durée, badge étude · Bible ou « Réunion autonome »,
  boutons Gestion de l'étude / Accueil / ⚙ / ?), stepper fixe cliquable,
  « Étape suivante » précise « (optionnelle) », « passer l'étape › », passage
  direct ②→⑥ sans invalidation (§9.3 testé) ; contenu par étape reprenant
  les pages existantes (③ éditeur v1 embarqué, ④ Reformulation, ⑤ Résumé en
  dialogue P17, ⑥ export) ; adaptateur de navigation pour les pages embarquées ;
  `AppWindow.ouvrir_reunion` (pile unique, jamais deux fois la même page).
- **P18.6c — Page Étude** : ruban (titre, thème, nombre de réunions, badge
  « Bible : [version] · versification : [édition] », boutons Modifier
  l'étude / Accueil / ⚙ / ?), réunions en mini-tuiles (rang, date, durée,
  avancement ①→⑤ SANS ⑥ — §9.4 testé au niveau UI, coût, Ouvrir, poignée
  ↑/↓ = ordre d'ouvrage persisté), « ＋ Ajouter une réunion » en menu,
  synthèse « Régénérer » / « Éditer » (saisie manuelle = version
  « manuel »), **renvoi Ouvrage** : `ui/ouvrage_window.py` (destination
  P19/P20 + export final P18.3 déplacé depuis la page Étude),
  `ui/modifier_etude_dialog.py`, `AppWindow.ouvrir_ouvrage`.
- **P18.6d — Exclusivité** (ARBITRAGE_EXCLUSIVITE_REUNIONS) : tous les points
  d'attachement passent par `services/rattachement.py` ; changement d'étude
  avec confirmation, **option A** : la référence seule change, découpage,
  reformulations, résumé et registre FID restent à l'ancienne étude (§9.5
  testé sur disque) ; détachement avec confirmation ; « Depuis une réunion
  autonome… » ne propose que les réunions sans étude.
- **P18.6e — Saisie manuelle** : un résumé est saisissable de zéro sans
  appel LLM (l'ancien `sauvegarder_edition` exigeait une version
  préexistante ; source par défaut d'une première saisie : brute corrigée) ;
  éditions manuelles de résumé tracées « édition manuelle » au journal
  (comme les blocs) ; invariant §9.6 testé : compilation d'ouvrage
  strictement identique entre version IA et version manuelle du même texte,
  aucune provenance dans le document.
- **P18.6f — Exports à 3 portées** : réunion — `assembler_reunion`
  (résumé validé en tête + reformulations validées dans l'ordre d'ouvrage,
  y compris intermédiaire ; seuls les textes VALIDÉS figurent, jamais un
  brouillon), bouton « Exporter les textes validés… » à l'étape ⑥ (la
  réunion autonome garde l'export de transcription v1) ; ouvrage — page
  Ouvrage ; résumé — inclus en tête de l'export de réunion.

### Invariants §9 de la spéc — couverture des tests

1. 0 ou 1 étude par réunion : `test_p18_6a_hub.py` (service) +
   `test_p18_6d_rattachement.py` (ajout refusé, rien d'écrit, changement
   confirmé/refusé).
2. Bandeau app uniquement sur l'accueil : `bandeau_app` présent sur le hub
   (a), absent des pages Réunion (b), Étude (c).
3. ④⑤ optionnelles, ②→⑥ direct sans invalidation : `test_p18_6b_reunion.py`
   (libellés, passage direct, contenus intacts, contour pointillé).
4. Page Étude sans ⑥ : `test_p18_6a_hub.py` (service) + `test_p18_6c_etude.py`
   (5 pastilles, pas de « ⑥ Export »).
5. Changement d'étude = option A : `test_p18_6a_hub.py` (fichiers conservés
   à l'ancienne étude) + `test_p18_6d_rattachement.py` (idem via le dialogue).
6. Saisie manuelle validée = résultat IA validé : `test_p18_6e_saisie_manuelle.py`
   (compilation identique, statut identique, aucune provenance).
7. Suggestions IA jamais insérées sans validation : dans le périmètre P18.6,
   garanti par l'assemblage (rien qu'un brouillon n'entre jamais dans un
   document — `test_p18_6f_exports.py`) ; le test complet (sous-titres,
   analyse de cohérence) arrive avec P19/P20 qui les définissent.
8. Pile sans doublon : `test_p18_6b_reunion.py` (réunion) + `test_p18_6c_etude.py`
   (ouvrage) — clés par chemin résolu.

### Décisions techniques de la session

1. **Définitions du stepper** (documentées dans `services/avancement.py`) :
   ① vert si journal de prétraitement présent ; ② vert si mots horodatés ;
   ③ vert si blocs de diarisation (bleu si transcription sans bloc) ;
   ④ vert si tous les FID actifs ont une version validée (bleu si résultats
   partiels) ; ⑤ vert si résumé validé (bleu si versions sans validation) ;
   ⑥ vert si trace d'export dans les réglages.
2. **Trace d'export dans les réglages** (`exports_reunions`), jamais dans le
   dossier du projet v1 (le projet v1 reste lisible tel quel, contrat §2).
3. **Exclusivité vérifiée aux moments de rattachement** (aucun registre
   global des études n'existe) : les études « connues » sont les études
   récentes des réglages ; les études existantes non conformes, s'il y en
   a, ne sont pas migrées (conforme à l'arbitrage).
4. **Page Réunion = adaptateur de navigation** : l'éditeur v1 et la page
   Reformulation embarqués appellent `navigation.*` sur la page Réunion
   (Accueil/Etude remontent à la pile, « Reformulation… » bascule sur
   l'étape ④ sans doublon de page).
5. **`ouvrir_correction` conservé** (page Éditeur directe de P16-bis) pour
   compatibilité ; les parcours utilisateur passent désormais par la page
   Réunion.
6. **Ordre d'ouvrage des réunions** : la poignée ↑/↓ de la page Étude
   réordonne `ordre_reunions` (l'ordre de réunion n'avait qu'une seule
   liste depuis P14.2 — c'est elle qui vaut ordre d'ouvrage, conforme à
   la spec §4.2 ; l'ordre d'ouvrage PAR BLOC, lui, reste P14.5).

### Écarts / points à arbitrer par l'atelier

- **« Nouvel audio… » depuis la page Étude** : guidage vers le hub (tuile
  « Nouvelle transcription ») puis rattachement (« Depuis une réunion
  autonome… » ou « Gestion de l'étude » de la page Réunion) — le flux de
  création complet n'a pas été dupliqué dans la page Étude (code additif,
  pas de refactor du workflow de transcription ; arbitrage bienvenu si
  l'atelier veut l'entrée directe).
- **Étapes ① et ② de la page Réunion** : panneaux d'information (état du
  journal, de la transcription) — relancer un prétraitement ou une
  transcription depuis la page Réunion n'est pas entré (le hub le permet
  sur une nouvelle réunion).
- **Page Ouvrage** : destination de navigation + export final uniquement —
  l'arborescence, le document compilé éditable et le rapport d'analyse
  restent P19/P20 (conforme à la consigne : seul le renvoi était concerné).
- **Invariant §9.7** (suggestions IA) : couvert localement (rien de
  non validé n'entre jamais dans un document) ; le test complet vient avec
  P19/P20.
- **Manuel utilisateur PDF** : non mis à jour (artefact v1 du packaging) ;
  la section « Études et navigation v2 » du README couvre la navigation,
  le rattachement et la saisie manuelle — mise à jour du manuel à
  programmer avec la prochaine livraison visible.

Bilan tests : **404 verts** (341 + 63 nouveaux : 20 P18.6a, 14 P18.6b,
10 P18.6c, 6 P18.6d, 5 P18.6e, 8 P18.6f). Aucune régression
P16/P16-bis/P17/P18/P18.5 (tests existants rejoués verts, y compris
`test_p16bis_*`, `test_p17_integration`).

---

## SESSION 2026-10-30 (P18.6-bis) — CORRECTIFS DE RELECTURE DE LA NAVIGATION : LIVRÉ

**Synchro atelier spec** (rituel) : 9 documents du 2026-10-30 recopiés dans
`architecture/spec_v2/` — SPEC_NAVIGATION_MODIFS_V2_2026-10-30c (fait autorité,
prime sur SPEC_NAVIGATION_V2 pour ses points), FEUILLE_DE_ROUTE_V2_2026-10-30c,
INDEX_SPECS_2026-10-30c, versions intermédiaires 30 et 30b conservées. Les
captures de relecture de David (2026-10-30) ont été prises après livraison
P18.6.

### Série 1 (§1-17) — hub, badges, page Étude

- **Hub** : trois GRANDES tuiles (classe `TuileAccueil` : icône + titre exact +
  paragraphe descriptif exact, textes de la spec ; clic = action) ;
  sous-titre « Prétraitement audio, transcription et reformulation assistés » ;
  « Version 2.0 » sans date ; **section Études retirée du hub** (invariant 1) —
  la tuile ouvre la **vue dédiée** `ui/etudes_window.py` (liste des études,
  Nouvelle étude, Ouvrir depuis un dossier… ; `AppWindow.ouvrir_etudes`).
- **Page Réunion** : aucun bandeau app ni rangée d'onglets (invariant 2, testé
  par QTabBar) ; bouton « Retour à l'étude » supprimé de l'éditeur v1 et de la
  page Reformulation (remplacé par « Gestion de l'étude » du ruban) ; badge
  au nom court de Bible (invariant 3 : Darby / Darby révisée / Segond 1910 —
  `services/bibles.py::nom_court_bible`).
- **Page Étude** : badge « Bible : Darby révisée · versification : Darby »
  (`versification_bible` — la Darby révisée garde la versification Darby) ;
  dates affichées = dates de RÉUNION (mtime de l'audio, `avancement.py::
  date_reunion`/`date_audio_projet` ; `rattacher` stocke la date de l'audio,
  invariant 4) ; titres de tuiles lisibles sans numérotation, rang
  « Réunion n » en annexe ; boutons par tuile Reformulation/Résumé retirés
  (Ouvrir + poignée de réordonnancement seulement, clic de tuile = ouvrir) ;
  pluriels propres ; en-tête « Réunions de l'étude » avec « ＋ Ajouter une
  réunion » à côté, en tête de liste.

### Série 2 (§18, §20) — stepper et actions

- **Plus aucun contour pointillé** (invariant 6) : aucune différence visuelle
  entre étapes obligatoires et optionnelles ; l'optionnalité ne se lit que dans
  le bouton « Étape suivante : … (optionnelle) » et l'info-bulle
  « Étape optionnelle ».
- **Bouton unique « Étape suivante : [nom] › »** (invariant 7) : « passer
  l'étape › » supprimé — le saut se fait par clic direct sur une pastille
  (toutes navigables).

### Série 3 (§19 réécrit) — stepper compact après transcription

- **Modèle compact** (invariant 5) : Transcription → Reformulation → Résumé →
  Export (①→④) ; les étapes Prétraitement / Transcription / Correction
  n'apparaissent plus séparément. La pastille « Transcription » fusionnée
  ouvre TOUJOURS l'éditeur de correction (invariant 8) ; **bleue** pendant la
  correction (transcription sans diarisation), **verte** quand la diarisation
  est validée (définition retenue pour « transcription corrigée validée »,
  documentée dans `services/avancement.py::etat_etape_transcription`).
- **Pas de stepper avant la transcription** (invariant 9) : mention discrète
  « transcription en attente » sur le hub, la page Étude et la page Réunion
  (la fenêtre de préparation audio reste linéaire, aucun stepper) ; la
  mention « transcription en cours » n'a pas de cas statique distinct (la
  transcription active est couverte par le dialogue de progression du hub) —
  à arbitrer si l'atelier veut une mention dédiée.
- **Transcrire un audio déjà prétraité = transcription directe** :
  `ProjectManager.trouver_projet_prepare` retrouve un dossier (copie de
  l'audio + audio_processed.wav + journal, sans .sttproj) ; confirmation puis
  transcription directe de l'audio traité, sans nouvelle étape de
  prétraitement.
- Page Étude : stepper Transcription → Reformulation → Résumé (jamais
  Export, invariant §9.4 maintenu).

### Invariants complémentaires 1-9 — couverture

1. Hub sans liste d'études : `test_p18_6bis_s1` (attributs + vue dédiée).
2. Pas de bandeau hors accueil, pas d'onglets : s1 (QTabBar) + s1 réunion.
3. Noms courts : s1 (`nom_court_bible`, badges réunion/étude).
4. Dates de réunion : s1 (`date_reunion` préfère l'audio, stockée au
   rattachement).
5. Stepper compact, page Étude sans Export : s3 + tests P18.6 ajustés.
6. Aucun pointillé : s2 + tests P18.6 ajustés.
7. Action unique : s2 (« passer » absent, libellé exact).
8. Pastille Transcription = éditeur : s3 (depuis toute étape).
9. Non transcrite = jamais de stepper : s3 (réunion, hub, page Étude).

### Décisions et écarts

- « Transcription corrigée validée » (pastille verte) = **diarisation
  validée** (blocs de parole présents) : le format v1 n'a pas de marqueur de
  validation de correction ; la diarisation validée est l'aboutissement
  documenté de la correction (à arbitrer si l'atelier veut un marqueur
  explicite).
- La détection « audio déjà prétraité » se fonde sur les traces sur disque
  (copie de l'audio + audio_processed.wav + journal, sans .sttproj) ; elle
  ne remonte pas au-delà des dossiers existants (les projets transcrits sont
  exclus).
- Les invariants §9 de SPEC_NAVIGATION_V2 restent verts (bandeau, pile,
  exclusivité, optionnalité, saisie manuelle, suggestion) — la feuille de
  correctifs ne fait que resserrer le visuel et le stepper.
- Manuel PDF toujours en attente de mise à jour (report existant) ; la
  section README « Études et navigation v2 » a été mise à jour (stepper
  compact, vue Études, dates, Version 2.0).

Bilan tests : **428 verts** (404 + 24 nouveaux : 13 série 1, 2 série 2,
9 série 3 — moins les tests P16-bis/P18.6 ajustés aux correctifs).

---

## SESSION 2026-10-30 (P18.6-bis, série 4) — TUILE ÉTUDES + TUILES : LIVRÉ

**Synchro atelier spec** (rituel) : 5 documents du 2026-10-30d/e recopiés —
SPEC_NAVIGATION_MODIFS_V2_2026-10-30e (fait autorité, prime sur la version
30c), INDEX_SPECS_2026-10-30e, versions 30d conservées, feuille de route
2026-10-30d inchangée.

### Série 4 (§21-22, spec 2026-10-30e)

- **§21 — Tuile « Études » = menu déroulant** : la page intermédiaire de
  choix (vue Études de la série 1) est SUPPRIMÉE (`ui/etudes_window.py`,
  `AppWindow.ouvrir_etudes`). Le menu, ancré à la tuile, liste les études
  (nom, nombre de réunions, pluriel propre), puis « ＋ Nouvelle étude » et
  « Ouvrir depuis un dossier… » ; choisir une étude ouvre DIRECTEMENT la
  page Étude ; sans étude, le menu l'indique et propose création/import ;
  Échap ou clic extérieur referment le menu (natif QMenu). Création et
  import revivent dans le hub (`creer_etude_ui`, `ouvrir_etude_dialogue`).
- **§22 — Tuiles conformes aux maquettes** : CONTOURS VISIBLES sur toutes
  les tuiles (bord 1 px net, fond de tuile distinct du fond de page) —
  couleurs EXACTES des maquettes en thème sombre (fond de tuile #2a2b31,
  bord #3a3b42, fond de page #1e1f24 appliqué au hub et à la page Étude,
  `theme_manager.py::couleurs_tuiles/BORD_BLEU_ACCENT/FOND_PAGE_SOMBRE`),
  équivalent sobre en thème clair. **Effet de survol** : élévation ~2 px
  animée (~120 ms, QVariantAnimation), contour au bleu d'accent #4a7db5,
  retour immédiat en sortie, curseur main — sur les 3 grandes cartes du
  hub ; les tuiles-rangées de la page Étude reçoivent contour + survol
  bleu + curseur main (l'élévation y est omise : widgets d'item d'une
  QListWidget dont le déplacement n'est pas fiable — écart documenté).
  Les 3 grandes cartes occupent 3 COLONNES égales (stretch identique).

### Reprise sur la maquette HTML (retour David du 2026-10-30)

La première passe du menu (QMenu brut) ne correspondait pas à la maquette
validée (`architecture/spec_v2/maquette-tuile-études-et-menu-déroulant-
transcriptstudio.html`) — reprise complète :

- **Icônes des tuiles** : les 3 SVG de la maquette (micro, dossier, livre
  ouvert — trait 1.6, bleu #6ea0d8, 34 px) créés dans `icons/`
  (`tuile-nouvelle-transcription.svg`, `tuile-reprendre.svg`,
  `tuile-etudes.svg`) ; plus aucune tuile sans icône.
- **Métriques de carte** : rayon 12 px, marges 22/20/18, icône 34 px avec
  10 px d'écart, titre 16 px, description 12 px à la couleur de la
  maquette (#a6a7ae en sombre — `couleurs_tuiles()["description"]`).
- **Menu = panneau déroulant** (`ui/menu_etudes.py`, `MenuEtudes`,
  Qt.Popup translucide de 320 px, ombre portée, rayon 12) — plus de QMenu :
  en-tête « VOS ÉTUDES » (majuscules espacées via QFont.setLetterSpacing) ;
  une ligne par étude (`LigneEtude`) : pastille de couleur stable par
  dossier (`couleur_pastille`, palette de la maquette), nom (le TITRE de
  l'étude, pas le nom de dossier — `rattachement.py::lire_etude_legere`
  lit titre/thème/modification d'etude.json sans charger l'étude),
  « [thème] · modifiée le 27 oct. 2026 » (`formater_date_modification`),
  badge « N réunions » (pastille #2b3444) ; séparateur ; actions
  « ＋ Nouvelle étude… » et « Ouvrir depuis un dossier… » (glyphe SVG) ;
  sans étude : « Aucune étude pour le moment » + les deux actions ;
  Échap referme (keyPressEvent), clic extérieur aussi (Qt.Popup natif) ;
  ancrage sous la tuile, aligné à gauche, 8 px d'écart
  (`MenuEtudes.ouvrir_sous`).
- Couleurs du panneau : `theme_manager.py::couleurs_menu_etudes`
  (maquette en sombre : #26272d, bord #3d4152, survol #2c2d33).

### Invariants — couverture

- Invariant 1 RÉÉCRIT (menu déroulant, jamais de page intermédiaire) :
  `test_p18_6bis_s1` (menu avec compte de réunions, ouverture directe,
  page « etudes » absente de la pile ; menu sans étude).
- §22 : `test_p18_6bis_s4` (couleurs exactes des maquettes, contour +
  survol + curseur main des cartes et tuiles-rangées, 3 colonnes égales,
  élévation 120 ms avec retour immédiat, un seul bouton « Ouvrir » +
  poignée ⠿ préservée, icônes des 3 tuiles, date française, pastille
  stable, lecture légère, couleurs du panneau).
- Invariant 1 / panneau de la maquette : `test_p18_6bis_s1` (panneau
  320 px, en-tête « Vos études », ligne d'étude avec titre/thème·date/
  badge, actions, ouverture directe, cas sans étude, Échap referme).
- Les 9 invariants complémentaires restent verts (séries 1-3), ainsi que
  les invariants §9 de SPEC_NAVIGATION_V2 ; aucune régression (436 verts).

Bilan tests : **442 verts** (436 + 6 nouveaux : icônes des tuiles, date
française, pastille stable, lecture légère, couleurs du panneau, Échap ;
menu réécrit sur la maquette dans les tests de la série 1).

---

## PROCHAINE ÉTAPE RECOMMANDÉE

**P18.6 et P18.6-bis (séries 1 à 4) sont LIVRÉS** (442 tests verts).
Restent :

1. **Recette P16/P17/P18/P18.6 par David** (checklist en fin de session
   P17 ci-dessus) : réunion Luc 1b de bout en bout avec vraie clé,
   jugement humain sur la fidélité, les jonctions de méditation et
   la « mémoire » de la 2ᵉ réunion (synthèse) ; P18 : références
   complétées vérifiables en un clic (Bibles installables depuis
   les réglages, onglet « Bibles »), export DOCX relu sous Word ;
   P18.6/P18.6-bis : parcours hub → réunion → étude (stepper
   compact, rattachement, changement d'étude, saisie manuelle,
   exports 3 portées, menu déroulant des études, tuiles et
   survol) contre les maquettes validées mises à jour.
2. **P19/P20 (v2.1)** — page Ouvrage complète (arborescence à la Word,
   document compilé éditable, rapport d'analyse, fusion de pensées,
   mobilité des paragraphes, sous-titres proposés par IA, export
   structuré) — la destination de navigation et l'export final sont
   déjà en place (P18.6).

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
  glisser-déposer) : couche de données complète et testée ; l'UI n'est pas
  entrée avec la page Traitement P16 (écart 7 de la session P16) — à placer
  en P19 (page Ouvrage) ou arbitrage atelier.

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
