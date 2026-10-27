# PROJECT_STATE.md - Etat actuel du développement TranscriptStudio

> **Dernière mise à jour** : 2026-10-27 (session P17 —
> **P17 LIVRÉ** : bloc Résumé + synthèse d'étude + récurrences ;
> P16 livré en attente de recette ; 228 tests verts)
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
  contexte, P17.3 récurrences entre réunions) — 228 tests verts.
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

## PROCHAINE ÉTAPE RECOMMANDÉE

**P16 et P17 sont LIVRÉS** (228 tests verts). Restent :

1. **Recette P16/P17 par David** (checklist en fin de session P17
   ci-dessus) : réunion Luc 1b de bout en bout avec vraie clé, jugement
   humain sur la fidélité, les jonctions de méditation et la
   « mémoire » de la 2ᵉ réunion (synthèse).
2. **P18** — JND locale (OSIS XML), validation des références et des
   citations (§5.2/§5.4), export DOCX de l'ouvrage, éventuelle
   pré-correction.

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
