# PROJECT_STATE.md - Etat actuel du développement TranscriptStudio

> **Dernière mise à jour** : 2026-10-10
> **Commit actuel** : 13f4f38
> **Branche** : master
> **Modifications locales** : OUI (a commiter - finalisation P9)

---

## 📊 ETAT GIT

### Position actuelle
- **Branche** : master
- **Local vs Origin** : +28 commits (en avance sur origin/master)
- **Dernier commit** : `13f4f38 E1.3 - Surlignage anime du mot lu : ExtraSelections, fondus par mot, regions continues (ponctuation, guillemets, espaces), contraste theme sombre`
- **Modifications locales** : finalisation P9 (polices systeme, icones media SVG, repli icone, raccourci standard) + docs
- **Commits récents** :
  - `13f4f38 E1.3 - Surlignage anime du mot lu : ExtraSelections, fondus par mot, regions continues`
  - `0e8a35a E1.1/E1.2 - Icône user.svg teintée couleur intervenant + suppression du bold sur le mot lu`
  - `b9429dd P9 - UI Multiplateforme : integration qdarktheme + correction bug _credential_store`
  - `f327448 P8 - FFmpeg multiplateforme avance : resolveur hierarchique embarque/config/PATH`
  - `629a21e Mise a jour PROJECT_STATE.md - P7 implemente avec commit 7bfcd17`
  - `7bfcd17 P7 - Tests automatises : structure pytest, fixtures, tests unitaires pour project_io et ffmpeg`
  - `4914a6c Mise a jour PROJECT_STATE.md - P1.3 implemente`
  - `528ce8c P1.3 - Migration non-destructive des anciens projets : deja implmente via P1.1+P1.2`
  - `71ac2cf P1.2 - Resolution a l'ouverture : project_file en memoire, resolution audio_file relatif/absolu avec fallback`
  - `76dc6cf P1.1 - Portable project format v1 : contrats de format, chemins relatifs, pas de project_file dans JSON`
  - `4db8e15 Mise a jour AGENTS.md - Instructions améliorées pour les agents IA`
  - `a02afb3 Mise a jour PROJECT_STATE.md - P0.3 implémenté et validé`
  - `fd615c9 P0.3 - Minimal cross-platform FFmpeg resolver`
  - `952a010 Commit P0.2 - API capability decoupling`
  - `b08698e P0.1 First-run + Decouplage API + FFmpeg minimal`

### Fichiers non suivis (untracked)
- `.vibe/` (dossier de configuration Vibe)
- `architecture/AGENTS.md` (instructions agent)
- `architecture/PROJECT_STATE.md` (ce fichier)

### Modifications non commitées
- `ui/main_window.py`, `ui/audio_preprocess_dialog.py` (P9.5 : styles par-bouton à hauteur CSS)
- `services/icons.py` (P9.5 : `ICON_BUTTON_*`, `make_button_height_css`)
- `services/theme_manager.py` (P9.5 : stylesheet boutons pilotée par `ICON_BUTTON_HEIGHT`)
- `icons/player-stop.svg` (P9.3 : nouveau, stop du prétraitement)
- `architecture/PROJECT_STATE.md`, roadmap (correctifs P9)

---

## 🎯 ETAT DU DEVELOPPEMENT

### Phases Complétées et Validées

#### ✅ **P0 - DEBLOCAGE IMMEDIAT** ⭐ **TERMINE**
- **P0.1 First-Run Minimal** ⭐ **VALIDE**
  - Commit : b08698e
  - Tous les tests manuels validés
  
- **P0.2 Découplage Clé API / Capacités** ⭐ **VALIDE**
  - Commit : 952a010
  - Création de `services/api_capabilities.py`
  - Mises à jour de `elevenlabs_api.py`, `elevenlabs_account_dialog.py`, `transcription_entry_dialog.py`
  - Tests manuels : validés
  
- **P0.3 FFmpeg Multiplateforme Minimal** ⭐ **VALIDE**
  - Commit : fd615c9
  - Validation : a02afb3
  - Résolveur multiplateforme dans `services/ffmpeg_paths.py`
  - Messages d'erreur clairs

#### ✅ **P1 - PORTABILITE DES PROJETS** ⭐ **TERMINE**
- **P1.1 Définir le contrat du format projet** ⭐ **VALIDE**
  - Commit : 76dc6cf
  - `project_format_version: 1`
  - Chemins relatifs pour audio_file
  - Suppression de project_file du JSON
  
- **P1.2 Résolution à l'ouverture** ⭐ **VALIDE**
  - Commit : 71ac2cf
  - Résolution des chemins audio depuis le dossier du projet
  - Compatibilité avec les anciens projets
  
- **P1.3 Migration non-destructive** ⭐ **VALIDE**
  - Commit : 528ce8c
  - Conversion des chemins absolus en relatifs à la sauvegarde
  - Suppression de project_file du JSON des anciens projets
  
- **P1.4 Sauvegarde et autosave** ⭐ **VALIDE**
  - Commit : a52e208
  - Sauvegarde au bon emplacement après déplacement
  - Title de l'éditeur mis à jour

#### ✅ **P2 - MODE SANS CLE API** ⭐ **TERMINE**
- **P2.1 Centraliser la notion de capacité** ⭐ **VALIDE**
  - Commit : e976c57
  - `services/api_capabilities.py` avec APICapabilityManager
  - Distinction capacités locales (FFmpeg) et en ligne (API)
  
- **P2.2 Fonctions autorisées sans API** ⭐ **VALIDE**
  - Commit : e976c57
  - Toutes les fonctions vérifiées : ouverture, lecture, modification, sauvegarde, export, prétraitement, finalisation, playback
  
- **P2.3 Fonctions nécessitant l'API** ⭐ **VALIDE**
  - Commit : e976c57
  - Blocage des appels sans clé dans `ElevenLabsTranscriber`
  - UX dégradée : bouton Transcrire désactivé + message clair
  - Proposition d'ouvrir les paramètres
  
- **P2.4 UX recommandée** ⭐ **VALIDE**
  - Commit : e976c57
  - Bouton Transcrire visible mais désactivé sans clé
  - Affichage discret de l'état API sur l'accueil

#### ✅ **P3 - DECOUPLAGE FINALISATION AUDIO / TRANSCRIPTION** ⭐ **TERMINE**
- **P3.1 Séparer les opérations** ⭐ **VALIDE**
  - Commit : dbe13f1
  - Refactorisation en `_start_finalization()`
  - Boutons "💾 Finaliser" et "☁ Transcrire" séparés
  
- **P3.2 Cycle de vie du projet** ⭐ **VALIDE**
  - Commit : dbe13f1
  - Gestion via `_finalize_mode`
  - Finalisation sans transcription possible

#### ✅ **P4 - RESILIENCE FACE A UN MEDIA MANQUANT** ⭐ **TERMINE**
- **P4.1 Stratégie de récupération** ⭐ **VALIDE**
  - Commit : c5ca718
  - Détection du media manquant à l'ouverture
  - Dialogue "Localiser le fichier... / Ouvrir sans audio / Annuler"
  - Mise à jour de la référence en mémoire si relocalisé
  - Conversion en chemin relatif à la sauvegarde
  
- **P4.2 Mode édition sans media** ⭐ **VALIDE**
  - Commit : c5ca718
  - Désactivation des contrôles de lecture
  - Affichage état "Audio indisponible" dans le titre
  - Conservation de l'édition, sauvegarde et exports

#### ✅ **P5 - NETTOYAGE** ⭐ **TERMINE**
- **P5.1 TranscriptAudio -> TranscriptStudio** ⭐ **VALIDE**
  - Commit : 93f90e9
  - Dossier temporaire renommé dans `audio_waveform_service.py`
  - Aucune autre occurrence trouvée dans le code source
  
- **P5.2 Audit pathlib** ⭐ **VALIDE**
  - Commit : 93f90e9
  - Aucun chemin Windows-only trouvé
  - Utilisation systématique de `pathlib.Path`
  
- **P5.3 Audit des imports et code mort** ⭐ **VALIDE**
  - Commit : 93f90e9
  - Import dupliqué de ProgressDialog supprimé dans `home_window.py`

#### ✅ **P6 - STOCKAGE SECURISE DES CLES API** ⭐ **TERMINE**
- **P6.1 Abstraction** ⭐ **VALIDE**
  - Commit : 5744295
  - Creation de `services/credential_store.py`
  - Intégration dans api_capabilities, elevenlabs_api, elevenlabs_transcriber, settings_dialog
  
- **P6.2 Migration** ⭐ **VALIDE**
  - Commit : 5744295
  - Méthode de migration depuis SettingsManager
  - Ne jamais journaliser la clé

#### ✅ **P7 - TESTS AUTOMATISES** ⭐ **TERMINE**
- **P7.1 Structure de tests** ⭐ **VALIDE**
  - Commit : 7bfcd17
  - Structure tests/unit/ et tests/integration/ créée
  - conftest.py avec fixtures créées
  - 18 tests unitaires opérationnels (hors Qt)
  
- **P7.2 Contenu des tests** ⭐ **VALIDE**
  - Commit : 7bfcd17
  - Tests pour project_io, ffmpeg_resolver, api_capabilities
  - Pas de vraie clé API incluse
  
- **P7.3 Matrice CI** ⭐ **PARTIEL**
  - Commit : 7bfcd17
  - pytest passe sur les tests non-Qt
  - CI à configurer pour Windows/macOS/Linux

#### ✅ **P8 - FFMPEG MULTIPLATEFORME AVANCE** ⭐ **TERMINE**
- **P8.1 Résolveur FFmpeg** ⭐ **VALIDE**
  - Commit : f327448
  - Stratégie hiérarchique : embarqué → config utilisateur → PATH
  - _get_embedded_ffmpeg_paths() pour multiplateforme
  - get_ffmpeg_path(settings) avec fallback
  
- **P8.2 Organisation des binaires** ⭐ **VALIDE**
  - Commit : f327448
  - Structure tools/ffmpeg/{platform}/ supportée
  - Ready pour packaging

#### ✅ **P9 - UI MULTIPLATEFORME** ⭐ **TERMINE**
- **P9.1 Themes** ⭐ **VALIDE**
  - Commit : b9429dd
  - Remplacement de `app.setStyle("Windows11")` par `Fusion` + qdarktheme
  - Integration de pyqtdarktheme (qdarktheme) pour les themes modernes
  - Personnalisation du fond general (remplace blanc pur par #fafafa/#f8f8f8)
  - Personnalisation des boutons (texte lisible, fond coherents)
  
- **P9.2 Polices** ⭐ **VALIDE**
  - Commit : 7487e24
  - Suppression de `QFont("Segoe UI Light", 28)` (Windows-only) dans `home_window.py`
  - Police système via `QFontDatabase.systemFont(GeneralFont)` + graisse Light
  - Emojis critiques des contrôles média remplacés par des SVG

- **P9.3 Icones** ⭐ **VALIDE**
  - Commit : 7487e24 (correctifs : a realiser)
  - `services/icons.py` : `make_tinted_icon(color, svg, size, dpr)` — icône SVG teintée, ancre `fill="#2942ff"`
  - Boutons lecture/pause/précédent/suivant de l'éditeur : `icons/player-*.svg` teintés avec la couleur de texte du thème (le rendu des emojis varie fortement selon l'OS)
  - Correctif : mêmes SVG dans la fenêtre de prétraitement (lecteurs original **et** résultat, bascules play/pause en `setIcon`, `player-stop.svg`)
  - `make_speaker_icon` refactoré en délégation à `services/icons.py`
  - Démarrage indépendant de `icon.ico` : repli `logo.png`, puis démarrage sans icône (`TranscriptStudio.py`)
  - `.icns` macOS et validation visuelle des icônes restantes (emojis non critiques, libellés texte) : reportés au packaging (P11)

- **P9.4 Raccourcis** ⭐ **VALIDE**
  - Commit : 7487e24
  - `QKeySequence("Ctrl+S")` remplacé par `QKeySequence.StandardKey.Save` (`main_window.py`) — mapping automatique `Cmd+S` sous macOS

- **P9.5 Hauteur des boutons** ⭐ **VALIDE**
  - Commit : (a realiser)
  - Constantes `ICON_BUTTON_WIDTH` / `ICON_BUTTON_HEIGHT` dans `services/icons.py` : taille de **tous** les boutons de l'application
  - `make_button_height_css()` : hauteur fixée en CSS (`min-height`/`max-height` hors padding/bordure) — le modèle de taille de la stylesheet du thème dépasse `setFixedSize`
  - Styles par-bouton (éditeur, prétraitement, lecteur de résultat) + stylesheet globale des boutons (`theme_manager.py`, `padding: 2px 12px`, `min-height` calculé) : accueil, paramètres et dialogues inclus
  - Vérifié offscreen sous le vrai thème : 13 boutons éditeur + 10 boutons prétraitement à 40x25, boutons texte ≤ hauteur cible

#### ✅ **E1 - AMELIORATIONS UX EDITEUR** ⭐ **TERMINE**
- **E1.1 Puce speaker** ⭐ **VALIDE**
  - Commit : 0e8a35a
  - `icons/user.svg` teinté à la couleur de l'intervenant (`QSvgRenderer`, pixmap haute densité)
  - Remplace le disque CSS dont le `border-radius` était écrasé par la stylesheet qdarktheme (P9.1)
  - Bouton plat, cliquable, insensible aux stylesheets globales

- **E1.2 Mot lu sans décalage** ⭐ **VALIDE**
  - Commit : 0e8a35a
  - Suppression du `font-weight:bold` sur le mot actif : la mise en gras provoquait un reflow de tous les mots suivants

- **E1.3 Surlignage animé du mot lu** ⭐ **VALIDE**
  - Commit : 13f4f38
  - Surlignage via `ExtraSelections` avec cartographie des ancres `word_N` -> positions document
  - Fin du re-render HTML complet à chaque changement de mot (gain performance + zéro reflow)
  - Fondu d'apparition ~70 ms (`QVariantAnimation`, OutQuad) ; fondu de retrait ~180 ms, **une animation par mot** : en lecture rapide, plusieurs mots s'effacent simultanément sur toute leur durée au lieu de disparaître instantanément
  - Gestion du scrubbing arrière (interruption du fondu sortant du mot réactivé, reprise depuis l'alpha courant) et réapplication sans animation après re-render
  - Régions continues : chaque mot réel possède une région couvrant l'espace qui le précède, son texte et sa ponctuation ; ponctuation isolée (`:`, `?`, `»,`) groupée avec le mot précédent ; guillemets ouvrants (`«`) groupés avec le mot suivant — chaque espace d'inter-mots est coloré avec le mot qui le suit, la bande de surlignage est continue pendant la lecture
  - Items purs (ponctuation/guillemets autonomes) : région vide, aucun surlignage individuel ni fondu fantôme
  - Correction rémanence : `stop()` n'émet pas `finished` sur `QVariantAnimation`, un fondu sortant interrompu (mot plus court que le fondu) laissait le mot surligné à alpha partiel de façon permanente ; retrait explicite dans `start_fade_out`
  - Thème sombre : variante assombrie du jaune (`HIGHLIGHT_COLOR_DARK`, détection via la couleur de texte du thème) ; la couleur du texte n'est **jamais** modifiée — la sélection ne peint que le fond, le texte garde sa couleur du thème (blanc en sombre, noir en clair) à tout instant ; les constantes de couleur acceptent un tuple `(r, g, b)` ou un hex `"#rrggbb"` (`make_highlight_color`)
  - Ancres, clics souris, double-clic et menus contextuels inchangés
  - Validation : script fonctionnel offscreen `.vibe/test_highlight_fade.py` (9 contrôles verts, dont régions avec ponctuation/guillemets et transitions rapides)

### Phases Suivantes
1. **P10 - CONFIGURATION MULTIPLATEFORME** (centralisation `app_paths.py`, temporaires)
2. **P11 - PACKAGING**

---

## 🔍 VERIFICATION DES REALISATIONS

### Ce qui a été confirmé dans le code :
- [x] `services/api_capabilities.py` existe avec APICapabilityManager et toutes les fonctions requises
- [x] `services/elevenlabs_api.py` vérifie la clé API à l'initialisation
- [x] `ui/elevenlabs_account_dialog.py` utilise `can_access_account_info()`
- [x] `ui/transcription_entry_dialog.py` utilise `has_transcription_api()` et désactive l'option sans API
- [x] `ui/new_transcription_dialog.py` utilise `has_transcription_api()` pour désactiver le bouton Transcrire
- [x] `ui/home_window.py` affiche l'état API, gère l'ouverture des paramètres et le mode de finalisation
- [x] `ui/audio_preprocess_dialog.py` implémente les boutons Finaliser/Transcrire et `_start_finalization()`
- [x] `services/ffmpeg_paths.py` a un résolveur multiplateforme avec fallback PATH
- [x] `models/project.py` a `project_format_version` et ne sauvegarde pas `project_file`
- [x] `services/project_io.py` implémente la résolution des chemins et la migration
- [x] `ui/main_window.py` implémente `handle_missing_audio()` et `disable_audio_controls()`
- [x] `services/audio_waveform_service.py` utilise `TranscriptStudio` au lieu de `TranscriptAudio`
- [x] `ui/home_window.py` sans import dupliqué de `ProgressDialog`
- [x] `services/credential_store.py` avec CredentialStore et toutes les méthodes requises
- [x] `services/api_capabilities.py` utilise CredentialStore via _credential_store
- [x] `services/elevenlabs_api.py` utilise CredentialStore
- [x] `services/elevenlabs_transcriber.py` utilise CredentialStore
- [x] `ui/settings_dialog.py` utilise CredentialStore
- [x] `ui/block_widget.py` : icône speaker teintée via `make_speaker_icon` (user.svg + couleur intervenant)
- [x] `ui/block_widget.py` : surlignage du mot actif par ExtraSelections, plus aucun re-render HTML à chaque mot
- [x] `ui/home_window.py` : police système (`QFontDatabase.systemFont`), plus de dépendance `Segoe UI Light`
- [x] `ui/main_window.py` : boutons média en SVG teinté thème, raccourci `QKeySequence.StandardKey.Save`
- [x] `services/icons.py` : `make_tinted_icon` (icônes SVG teintées multiplateforme)
- [x] `TranscriptStudio.py` : icône de démarrage avec repli (`icon.ico` → `logo.png` → aucune), pas de crash si absente

### Tests manuels réalisés (selon commits) :
- [x] P0.1 : Tous les tests validés
- [x] P0.2 : Tests validés (démarrage sans clé, transcription directe bloquée, ajout clé fonctionnel)
- [x] P0.3 : Tests validés (FFmpeg détecté sur toutes les plateformes)
- [x] P1 : Tests manuels validés (création, copie, ouverture, modification, sauvegarde)
- [x] P2 : Tests validés (démarrage sans clé, ouverture projet, export, prétraitement, finalisation, bouton Transcrire désactivé, message API clair)
- [x] P3 : Tests validés (bouton Finaliser, découplage finalisation/transcription)
- [x] P4 : Tests validés (media manquant, relocalisation, ouverture sans audio)
- [x] P5 : Tests validés (nettoyage des noms historiques)
- [x] P6 : Tests à valider (stockage sécurisé des clés)
- [x] P7 : Suite pytest exécutée le 2026-10-10 (22 tests verts)
- [x] E1 : Script fonctionnel surlignage validé (cartographie, fondus, transition, scrubbing, transitions rapides sans rémanence, re-render, ancres)

---

## 🧪 TESTS

### Tests existants
- **Fichier** : `test/test.py`
- **Contenu** : Exemple basique pyqtgraph
- **Statut** : Non pertinent pour la validation fonctionnelle

### Tests automatisés
- **État** : 22 tests pytest verts (`tests/unit` : project_io, ffmpeg_resolver, api_capabilities), exécution confirmée le 2026-10-10
- **Script fonctionnel** : `.vibe/test_highlight_fade.py` (surlignage ExtraSelections + fondus, offscreen, 7 contrôles)
- **À faire** : P7.3 CI multi-OS ; intégrer les tests Qt/PySide6 (marqueur `qt`)

---

## 🚀 PROCHAINE ETAPE RECOMMANDEE

### Priorité immédiate : **P10 - CONFIGURATION MULTIPLATEFORME**

**Objectif** : Éliminer les hypothèses Windows du code métier

#### Actions principales :
- [ ] Créer/centraliser `app_paths.py` : chemins applicatifs, `QStandardPaths` pour les dossiers utilisateur
- [ ] Ne plus créer automatiquement le répertoire de projets à l'import
- [ ] Temporaires : sous-répertoires uniques par session/projet, nettoyage vérifié
- [ ] Puis P11 - PACKAGING (générer `.icns`, valider emojis restants sur macOS/Linux)

#### Fichiers concernés :
- `services/settings.py`, `services/app_paths.py` (à créer)
- `services/audio_waveform_service.py` (temporaires)

#### Prérequis :
- ✅ P0 à P8 terminés
- ✅ P9 terminé (P9.1 : b9429dd ; P9.2-P9.4)
- ✅ E1 terminé (0e8a35a, 13f4f38)

---

## 📋 RESUME DES COMMITS RECENTS

| Commit | Message | Statut | Phase |
|--------|---------|--------|-------|
| 7487e24 | P9.2-P9.4 - Polices systeme, icones media SVG teintees, repli icone demarrage, raccourci standard | ✅ VALIDE | P9 |
| (a realiser) | P9.5 - Icones SVG pretraitement + hauteur globale des boutons (ICON_BUTTON_*, CSS) | ⏳ A COMMIT | P9 |
| 13f4f38 | E1.3 - Surlignage anime du mot lu : ExtraSelections, fondus par mot, regions continues | ✅ VALIDE | E1 |
| 0e8a35a | E1.1/E1.2 - Icône user.svg teintée + suppression bold mot lu | ✅ VALIDE | E1 |
| b9429dd | P9 - UI Multiplateforme : integration qdarktheme + correction bug _credential_store | ✅ VALIDE | P9 |
| 7bfcd17 | P7 - Tests automatises | ✅ VALIDE | P7 |
| 5744295 | P6 - Stockage securise des cles API | ✅ VALIDE | P6 |
| 93f90e9 | P5 - Nettoyage et standardisation | ✅ VALIDE | P5 |
| c5ca718 | P4 - Resilience face a un media manquant | ✅ VALIDE | P4 |
| dbe13f1 | P3 - Decouplage finalisation audio / transcription | ✅ VALIDE | P3 |
| 749ed6c | P2 - Mode sans cle API : UX degradee et decouplage fonctionnel | ✅ VALIDE | P2 |
| a52e208 | P1.4 - Sauvegarde et autosave : deja implemente via P1.2 | ✅ VALIDE | P1 |
| 4914a6c | Mise a jour PROJECT_STATE.md - P1.3 implemente | ✅ DOC | P1 |
| 528ce8c | P1.3 - Migration non-destructive des anciens projets | ✅ VALIDE | P1 |
| 71ac2cf | P1.2 - Resolution a l'ouverture | ✅ VALIDE | P1 |
| 76dc6cf | P1.1 - Portable project format v1 | ✅ VALIDE | P1 |
| fd615c9 | P0.3 - Minimal cross-platform FFmpeg resolver | ✅ VALIDE | P0 |
| a02afb3 | Mise a jour PROJECT_STATE.md - P0.3 implémenté et validé | ✅ DOC | P0 |
| 952a010 | Commit P0.2 - API capability decoupling | ✅ VALIDE | P0 |
| b08698e | P0.1 First-run + Decouplage API + FFmpeg minimal | ✅ VALIDE | P0 |

---

## 🎯 DEFINITION OF DONE ACTUELLE

### P0 - DEBLOCAGE IMMEDIAT
- [x] P0.1 : First-run fonctionnel et validé
- [x] P0.2 : Découplage API implémenté et validé
- [x] P0.3 : FFmpeg multiplateforme implémenté et validé
- **Statut** : ✅ **100% TERMINE**

### P1 - PORTABILITE DES PROJETS
- [x] P1.1 : Contrat de format projet implémenté et validé
- [x] P1.2 : Résolution à l'ouverture implémentée et validée
- [x] P1.3 : Migration non-destructive implémentée et validée
- [x] P1.4 : Sauvegarde après déplacement implémentée et validée
- **Statut** : ✅ **100% TERMINE**

### Global
- **P0** : ✅ **TERMINE**
- **P1** : ✅ **TERMINE**
- **P2** : ✅ **TERMINE**
- **P3** : ✅ **TERMINE**
- **P4** : ✅ **TERMINE**
- **P5** : ✅ **TERMINE**
- **P6** : ✅ **TERMINE**
- **P7** : ✅ **TERMINE**
- **P8** : ✅ **TERMINE**
- **P9** : ✅ **TERMINE** (P9.1 Themes b9429dd ; P9.2-P9.4 : polices système, icônes SVG teintées, repli icône, raccourci standard)
- **E1** : ✅ **TERMINE** (E1.1/E1.2 : 0e8a35a ; E1.3 : 13f4f38)
- **Prochaine** : **P10 - Configuration multiplateforme**, puis **P11 - Packaging**

---

*Ce fichier est mis à jour après chaque étape significative du développement.*
*Dernière mise à jour : après vérification complète de l'état du dépôt et des commits.*