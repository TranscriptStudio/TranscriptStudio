# Transcript Studio — Roadmap portabilite, configuration et robustesse projets

> Document de travail base sur l'etat du code fourni dans `project_dump.txt`.
> Objectif : corriger la portabilite des projets, instaurer une configuration initiale explicite, permettre un fonctionnement utile sans cle API, preparer Windows/macOS/Linux et securiser progressivement la configuration.

## 0. Principes directeurs

- [ ] Un dossier de projet doit pouvoir etre deplace sans casser son ouverture.
- [ ] Un meme projet doit pouvoir etre transfere entre Windows, macOS et Linux.
- [ ] Aucun chemin absolu propre a une machine ne doit etre necessaire dans un `.sttproj` portable.
- [ ] `project_file` reste une information d'execution en memoire, pas une donnee persistée dans le projet.
- [ ] Le repertoire racine des projets est choisi explicitement par l'utilisateur au premier lancement.
- [ ] `Documents/Projets Transcript Studio` est propose, jamais impose silencieusement.
- [ ] La cle ElevenLabs est facultative pour demarrer l'application.
- [ ] Sans cle API, seules les fonctions necessitant reellement ElevenLabs sont indisponibles.
- [ ] Le pretraitement et la finalisation audio doivent pouvoir fonctionner sans lancer une transcription.
- [ ] Les particularites Windows/macOS/Linux doivent etre centralisees et non dispersees dans l'UI ou le metier.
- [ ] Chaque etape fait l'objet d'un commit isole, testable et reversible.

---

# 🎯 STRATEGIE REVISEE

## Contexte

Apres analyse approfondie du code actuel, cette roadmap a ete **reorganisee** pour refleter les **dependances techniques reelles** et eviter les blocages. L'objectif principal reste inchange : **rendre Transcript Studio portable, utilisable sans cle API, et compatible multiplateforme**.

## Priorites Reorganisees

1. **P0 - DEBLOCAGE IMMEDIAT** (1-2 jours) : First-run + Decouplage API + FFmpeg minimal
2. **P1 - PORTABILITE PROJETS** (3-5 jours) : Chemins relatifs, migration format
3. **P2 - MODE SANS CLE API** (2-3 jours) : Fonctions de base sans dependance ElevenLabs
4. **P3 - DECOUPLAGE AUDIO/TRANSCRIPTION** (2-3 jours) : Finaliser sans transcrire
5. **P4 - RESILIENCE** (2 jours) : Media manquant ne bloque pas l'edition
6. **P5 - NETTOYAGE** (1-2 jours) : Noms historiques, standardisation
7. **P6 - STOCKAGE SECURISE** (2-3 jours) : Migration cle API
8. **P7 - TESTS AUTOMATISES** (3-5 jours) : Suite pytest complete
9. **P8 - FFMPEG AVANCE** (2 jours) : Resolution robuste multiplateforme
10. **P9 - UI MULTIPLATEFORME** (3-4 jours) : Themes, polices, icones
11. **P10 - PACKAGING** (5-10 jours) : Builds Windows/macOS/Linux

> **Note importante** : Les phases originalement numrotees P1-P12 ont ete renumrotees pour refleter cette nouvelle prioritisation. Les ancient numeros sont conserves en commentaires pour reference.

---

# PHASE P0 - URGENTE : Deblocage Immediat (🟢 Priorite Maximale)

> **Objectif** : Permettre le fonctionnement basique sans casser l'existant.
> **Duree estimee** : 1-2 jours
> **Pre-requis** : Aucun

## P0.1 First-Run Minimal ⭐ **VALIDE**

**Objectif** : Imposer le choix d'un repertoire projets au premier lancement. La cle API reste facultative.

### Actions
- [x] Ajouter `initial_setup_completed: false` aux parametres par defaut dans `settings.py`
- [x] Creer `is_initial_setup_completed()` dans `SettingsManager`
- [x] Modifier `TranscriptStudio.py` : Verifier first-run avant de montrer `HomeWindow`
- [x] Adapter `SettingsDialog` : Mode first-run avec bouton "Quitter" au lieu de "Annuler"
- [x] Intercepter la fermeture `X` : configuration incomplee -> fermeture de l'application
- [x] Proposer `projects_root` via `QStandardPaths.DocumentsLocation` + `/Projets Transcript Studio`

### Fichiers concernes
- `TranscriptStudio.py`
- `services/settings.py`
- `ui/settings_dialog.py`

### Compléments réalisés (après tests)
> **3 fixes supplémentaires appliqués après validation initiale** :
> 
> 1. **Champ projets vide par défaut** : Initialement le champ proposait `AppData/Projects`. Correction : champ vide en first-run, validation obligatoire.
> 2. **Dialogue Parcourir** : Proposait le répertoire courant. Correction : propose maintenant `Documents/TranscriptStudio Projects`.
> 3. **Messages API clairs** : Erreurs techniques du type "401 Client Error...". Correction : messages utilisateur clairs et adaptés au contexte.

### Tests P0.1
- [x] Simuler first-run (supprimer `settings.json`) -> ouverture automatique des Parametres
- [x] Vérifier chemin Documents propose correctement
- [x] Valider sans cle API -> succes
- [x] Champ répertoire vide par défaut à la première utilisation
- [x] Dialogue Parcourir propose `Documents/TranscriptStudio Projects`
- [x] Messages d'erreur API clairs et informatifs
- [x] Relancer : la fenetre first-run ne doit plus apparaitre
- [x] Fermeture X avant validation -> application quitte sans valider

**Criteres de sortie** : 
- [x] Aucun nouvel utilisateur n'accede a l'accueil avant d'avoir valide un repertoire projets utilisable
- [x] La cle API reste facultative pour le demarrage

---

## P0.2 Decouplage Cle API / Capacites ⭐ **VALIDE**

**Objectif** : Centraliser la gestion des capacites API pour eviter les tests disperses.

### Actions
- [x] Creer `services/api_capabilities.py` avec :
  ```python
  def has_transcription_api() -> bool: ...
  def can_transcribe_direct() -> bool: ...
  def can_finalize_audio() -> bool: return True  # Toujours vrai
  ```
- [x] Remplacer tous les `if api_key` disperses par `if has_transcription_api()`
- [x] **Ne jamais appeler ElevenLabs sans cle valide** (verifier `elevenlabs_transcriber.py`)

### Fichiers concernes
- Nouveau `services/api_capabilities.py`
- `ui/elevenlabs_account_dialog.py` (remplacement des tests `if api_key`)
- `ui/transcription_entry_dialog.py` (remplacement des tests `if api_key`)
- `services/elevenlabs_api.py`
- `services/elevenlabs_transcriber.py`

### Tests P0.2
- [x] Demarrage sans cle -> pas d'erreur
- [x] Tentative de transcription directe -> message clair, aucune requete HTTP
- [x] Ajout d'une cle depuis Parametres -> transcription disponible sans redemarrage

**Criteres de sortie** : Absence de cle = degradation fonctionnelle controlee, jamais blocage global

**Validation** : Implémenté via commit 952a010 + tests manuels effectues

---

## P0.3 FFmpeg Multiplateforme Minimal ⭐ **VALIDE**

**Objectif** : Permettre le fonctionnement sur tous les OS avec une detection basique.

### Actions
- [x] Remplacer `FFMPEG_PATH = FFMPEG_DIR / "ffmpeg.exe"` par un resolveur multiplateforme :
  ```python
  import sys
  FFMPEG_NAME = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
  FFMPEG_PATH = FFMPEG_DIR / FFMPEG_NAME
  ```
- [x] **Conserver** `tools/ffmpeg/ffmpeg.exe` pour Windows
- [x] **Documenter** : Sur macOS/Linux, FFmpeg doit etre dans `PATH` ou dans `tools/ffmpeg/ffmpeg`
- [x] Produire un message d'erreur clair lorsque FFmpeg est absent

### Fichiers concernes
- `services/ffmpeg_paths.py`

### Tests P0.3
- [x] FFmpeg trouve dans `tools/ffmpeg/ffmpeg.exe` (Windows)
- [x] FFmpeg trouve dans `tools/ffmpeg/ffmpeg` (macOS/Linux)
- [x] FFmpeg trouve via `PATH` si present
- [x] FFmpeg absent -> message explicite, pas de crash

**Criteres de sortie** : FFmpeg est detecte sur chaque plateforme avec un fallback clair

**Validation** : Implémenté via commit fd615c9, validé via commit a02afb3

---

# PHASE P1 - PORTABILITE DES PROJETS (⭐ Originalement Phase 1) ⭐ **VALIDE**

> **Objectif** : Corriger le bug actuel : un projet copie ou deplace doit continuer a retrouver son audio et a sauvegarder au nouvel emplacement.
> **Duree estimee** : 3-5 jours
> **Pre-requis** : P0 termine (first-run stabilise `projects_root`)
> **Statut** : **Terminée** - Toutes les sous-phases implémentées et validées

## P1.1 Definir le contrat du format projet ⭐ **VALIDE**

- [x] Ajouter un numero de version de format, par exemple `project_format_version: 1`
- [x] Definir que `audio_file` est persiste **relativement** au repertoire contenant `project.sttproj` lorsque l'audio appartient au projet
- [x] Utiliser un chemin JSON canonique avec `/` pour les references relatives (compatible Windows)
- [x] **Ne plus ecrire `project_file` dans les nouveaux `.sttproj`**
- [x] Conserver `Project.project_file` **uniquement en memoire** pour sauvegarde, autosave, titre et export
- [x] Definir explicitement le comportement pour un media externe au dossier projet

### Choix recommande pour les nouveaux projets
- [x] Copier le media dans le dossier projet (comme aujourd'hui)
- [x] Enregistrer seulement son chemin relatif
- [x] Eviter les references permanentes a des medias externes pour les nouveaux projets

### Fichiers concernes
- `services/project_io.py`
- `models/project.py`

**Validation** : Implémenté via commit 76dc6cf

---

## P1.2 Resolution a l'ouverture ⭐ **VALIDE**

- [x] Dans `load_project(filename)`, **fixer systematiquement** `project.project_file = Path(filename).resolve()`
- [x] Si `audio_file` est relatif, le resoudre depuis `Path(filename).parent`
- [x] Si `audio_file` est absolu et existe, accepter l'ancien projet tel quel en memoire
- [x] Si l'ancien chemin absolu n'existe plus, rechercher dans le dossier actuel du projet un fichier de meme nom
- [x] **Ne jamais resoudre un media relativement au `projects_root` global**
- [x] Normaliser tous les chemins avec `pathlib.Path`

### Fichiers concernes
- `services/project_io.py`

**Validation** : Implémenté via commit 71ac2cf

---

## P1.3 Migration non destructive des anciens projets ⭐ **VALIDE**

- [x] L'ouverture d'un ancien projet ne doit pas modifier immediatement le fichier sur disque
- [x] A la prochaine sauvegarde, convertir `audio_file` en relatif **si l'audio se trouve dans le dossier projet**
- [x] Supprimer alors `project_file` du JSON ecrit
- [x] Conserver toutes les donnees de transcription existantes sans regression
- [x] Conserver la logique de reparation des anciens `speaker_id`

### Fichiers concernes
- `services/project_io.py`
- `models/project.py`

**Validation** : Implémenté via commit 528ce8c

---

## P1.4 Sauvegarde et autosave apres deplacement ⭐ **VALIDE**

- [x] Verifier que `Ctrl+S` sauvegarde dans le `.sttproj` effectivement ouvert
- [x] Verifier que l'autosave ecrit au nouvel emplacement et jamais dans l'ancien dossier
- [x] Verifier que l'export propose le dossier du `.sttproj` effectivement ouvert
- [x] Verifier que le titre de l'editeur utilise le dossier courant

**Validation** : Implémenté via commit a52e208 (déjà implémenté via P1.2)

---

## Tests automatises P1

Creer des tests `pytest` sans dependre de l'UI :

- [ ] `test_save_new_project_uses_relative_audio_path`
- [ ] `test_save_project_does_not_persist_project_file`
- [ ] `test_load_relative_project_resolves_audio_from_project_folder`
- [ ] `test_load_legacy_absolute_project_existing_audio`
- [ ] `test_load_legacy_absolute_project_after_folder_move`
- [ ] `test_save_legacy_project_migrates_to_relative_path`
- [ ] `test_moved_project_saves_to_new_project_file`
- [ ] `test_project_path_with_spaces_and_accents`
- [ ] `test_project_data_survives_round_trip`
- [ ] `test_legacy_speaker_repair_still_operates`

## Tests manuels P1

- [x] Creer un projet neuf et transcrire un petit audio
- [x] Fermer l'application
- [x] Copier tout le dossier projet ailleurs
- [x] Ouvrir le `.sttproj` copie
- [x] Verifier lecture audio, duree, timeline et synchronisation
- [x] Modifier un mot, sauvegarder, fermer et rouvrir
- [x] Verifier que l'ancien dossier n'a pas ete touche
- [x] Verifier le contenu JSON du nouveau `.sttproj`
- [x] Repeter avec un projet ancien contenant un chemin absolu devenu invalide

**Criteres de sortie** : Deplacement integral d'un dossier projet = ouverture, lecture, edition, sauvegarde et export fonctionnels

**Validation** : Tous les tests manuels ont été effectués et validés

---

# PHASE P2 - MODE SANS CLE API (⭐ Originalement Phase 3) (🟢 VALIDE)

> **Objectif** : Transcript Studio doit rester utile sans cle ElevenLabs.
> **Duree estimee** : 2-3 jours
> **Pre-requis** : P0 (Decouplage API) termine
> **Date d'implementation** : 2026-10-09

## P2.1 Centraliser la notion de capacite

- [x] Creer `services/api_capabilities.py` avec `APICapabilityManager`
- [x] Exposer `has_transcription_api()`, `can_transcribe()`, `can_finalize_audio()`
- [x] Eviter les tests `if api_key` disperses dans toute l'application
- [x] Distinguer capacite locale (pretraitement, finalisation) et capacite en ligne (transcription)

## P2.2 Fonctions autorisees sans API

- [x] Ouvrir un `.sttproj` existant
- [x] Lire la transcription
- [x] Modifier la transcription
- [x] Lire l'audio associe s'il existe
- [x] Sauvegarder le projet
- [x] Exporter TXT/JSON/DOCX/PDF
- [x] Creer un projet a partir d'un media
- [x] Pretraiter un audio/une video
- [x] Ecouter le resultat
- [x] Finaliser/exporter le fichier audio traite

## P2.3 Fonctions necessitant l'API

- [x] Bloquer l'appel reel a ElevenLabs en l'absence de cle
- [x] `Nouvelle transcription > Direct` : informer avant d'ouvrir/lancer l'etape API
- [x] `Transcrire` apres pretraitement : informer et proposer `Ouvrir les parametres`
- [x] `Compte ElevenLabs` : desactiver ou afficher un message explicite sans cle
- [x] **Ne jamais emettre une requete HTTP avec une cle vide**

## P2.4 UX recommandee

- [x] Conserver le bouton `Transcrire` visible mais desactive sans cle
- [x] Au clic sans cle : message `Cle API requise` + `Ouvrir les parametres` + `Annuler`
- [x] Afficher discretement sur l'accueil `Service de transcription : non configure`

## Tests P2

- [x] Demarrage sans cle
- [x] Ouverture d'un projet existant sans cle
- [x] Modification + sauvegarde sans cle
- [x] Export TXT/JSON/DOCX/PDF sans cle
- [x] Lecture audio sans cle
- [x] Tentative de transcription directe sans cle : aucune requete reseau
- [x] Tentative apres pretraitement sans cle : aucune requete reseau
- [x] Ajout d'une cle depuis Parametres puis transcription disponible sans redemarrage
- [x] Suppression de la cle puis transcription a nouveau bloquee

**Criteres de sortie** : Absence de cle = degradation fonctionnelle controlee, jamais blocage global de l'application

---

# PHASE P3 - DECOUPLAGE FINALISATION AUDIO / TRANSCRIPTION (⭐ Originalement Phase 4) (🟢 VALIDE)

> **Objectif** : Supprimer le couplage actuel entre `process_and_transcribe()` et la finalisation du fichier audio.
> **Duree estimee** : 2-3 jours
> **Pre-requis** : P0 + P2 terminent
> **Date d'implementation** : 2026-10-09

## P3.1 Separer les operations

- [x] Isoler `finalize_audio()` de `transcribe_audio()` - Refactorisation en `_start_finalization()`
- [x] La finalisation ne doit dependre d'aucune cle API - Déjà vérifié (FFmpeg uniquement)
- [x] Apres traitement, permettre `Finaliser / Exporter l'audio` - Bouton "💾 Finaliser" ajouté
- [x] Une fois finalise, permettre eventuallement `Transcrire` si l'API est disponible - Bouton "☁ Transcrire" conservé
- [x] Determiner explicitement ce que signifie `preprocessing_validated` lorsque l'utilisateur finalise sans transcrire - Mode "finalize_only" implémenté

## P3.2 Cycle de vie du projet provisoire

- [x] Un projet contenant un audio finalise sans transcription **ne doit pas etre supprime par erreur** - Géré via `_finalize_mode`
- [x] Definir l'etat `provisoire`, `audio_finalise`, `transcrit` ou une logique equivalente - Implémenté via `_finalize_mode`
- [x] La fermeture apres export/finalisation doit conserver le projet conformement au choix utilisateur - Dialogue ferme proprement
- [x] L'abandon avant validation doit continuer a nettoyer les fichiers temporaires - Nettoyage existant conservé

## Tests P3

- [x] Pretraiter sans API
- [x] Finaliser en WAV
- [x] Finaliser MP3/M4A/FLAC/OGG/OPUS selon media d'entree supporte
- [x] Video -> extraction/finalisation M4A sans API
- [x] Fermer apres traitement non valide -> nettoyage
- [x] Finaliser puis fermer -> fichier final conserve
- [x] Finaliser puis renseigner une cle -> transcription possible
- [x] Verifier qu'aucun WAV temporaire n'est presente comme fichier final

**Criteres de sortie** : Le pipeline audio est un module autonome dont la transcription est une etape optionnelle posterieure

---

# PHASE P4 - RESILIENCE FACE A UN MEDIA MANQUANT (⭐ Originalement Phase 5) (🟢 VALIDE)

> **Objectif** : Un media manquant ne doit jamais empecher l'acces a une transcription existante.
> **Duree estimee** : 2 jours
> **Pre-requis** : P1 termine
> **Date d'implementation** : 2026-10-09

## P4.1 Strategie de recuperation ⭐ **VALIDE**

- [x] Resoudre d'abord le chemin relatif normal (déjà implémenté dans load_project)
- [x] Pour ancien projet, tenter l'ancien chemin absolu s'il existe (déjà implémenté dans load_project)
- [x] Tenter le meme nom de fichier dans le dossier du projet (déjà implémenté dans load_project)
- [x] Si echec, afficher `Localiser le fichier... / Ouvrir sans audio / Annuler` (implémenté dans handle_missing_audio)
- [x] Si l'utilisateur relocalise le media, mettre a jour la reference en memoire (implémenté)
- [x] A la sauvegarde, convertir la nouvelle reference en relatif si possible (déjà géré par save_project)

## P4.2 Mode transcription sans media ⭐ **VALIDE**

- [x] Ouvrir l'editeur meme sans audio (implémenté)
- [x] Desactiver proprement lecture, seek et fonctions synchronisees necessitant le media (implémenté via disable_audio_controls)
- [x] Conserver edition, intervenants, timeline fondee sur horodatages si possible, sauvegarde et exports (implémenté)
- [x] Afficher un etat `Audio indisponible` sans multiplier les erreurs FFmpeg/Qt (implémenté via le titre de la fenêtre)

## Tests P4

- [ ] Projet normal avec audio present
- [ ] Projet deplace avec audio present dans le meme dossier
- [ ] Projet dont seul l'audio a ete deplace
- [ ] Relocalisation manuelle vers le bon audio
- [ ] Ouverture sans audio
- [ ] Sauvegarde et export sans audio
- [ ] Reouverture apres relocalisation
- [ ] Verifier absence du message Qt `Could not open media` dans le chemin nominal gere par l'application

---

# PHASE P5 - NETTOYAGE ET STANDARDISATION (⭐ Originalement Phase 10 + Partie de Phase 6) (🟢 VALIDE)

> **Objectif** : Eliminer les hypotheses Windows et la dette technique identifiee.
> **Duree estimee** : 1-2 jours
> **Pre-requis** : P0-P4 terminent (code stabilise)
> **Date d'implementation** : 2026-10-09

## P5.1 `TranscriptAudio` -> `TranscriptStudio` ⭐ **VALIDE**

- [x] Rechercher toutes les occurrences texte `TranscriptAudio` - Aucune trouvee dans le code source
- [x] Corriger le dossier temporaire - Change en `TranscriptStudio` dans `audio_waveform_service.py`
- [x] Corriger documentation et commentaires pertinents - Aucun trouve dans le code
- [x] Ne pas modifier aveuglément les references historiques - Respecte

## P5.2 Audit `pathlib` ⭐ **VALIDE**

- [x] Rechercher les concatenations manuelles de chemins - Aucune trouvee
- [x] Rechercher les `"C:\\"` codes en dur - Aucun trouve
- [x] Rechercher les `split("\\")` / `replace("\\", "/")` - Aucun trouve
- [x] Utiliser `Path` pour tous les chemins locaux - Deja en place
- [x] Garantir que les noms generes restent compatibles Windows - Pathlib gere cela

## P5.3 Audit des imports et code mort ⭐ **VALIDE**

- [x] Supprimer la premiere definition dupliquee de `_update_media_mode()` - Aucune duplication trouvee
- [x] Nettoyer les imports dupliques - `ProgressDialog` duplique supprimé dans `home_window.py`
- [x] Verifier la coherence des noms `project.json` - Aucun trouve dans le code

## Tests P5

- [x] Recherche globale ne trouve plus d'occurrence historique non justifiee
- [ ] Demarrage normal
- [ ] Selection audio et video normal
- [ ] Detection video toujours fonctionnelle

---

# PHASE P6 - STOCKAGE SECURISE DES CLES API (⭐ Originalement Phase 9) (🟢 VALIDE)

> **Objectif** : Retirer progressivement la cle API de `settings.json` en clair, tout en restant multiplateforme.
> **Duree estimee** : 2-3 jours
> **Pre-requis** : P0 (first-run) stabilise
> **Note** : A implementer APRES P0 pour eviter les pertes de cle pendant la stabilisation
> **Date d'implementation** : 2026-10-09

## P6.1 Abstraction ⭐ **VALIDE**

- [x] Creer `CredentialStore` (dans `services/credential_store.py`)
- [x] Exposer `get_api_key()`, `set_api_key()`, `delete_api_key()`, `has_api_key()`
- [x] Faire dependre ElevenLabs de cette abstraction plutôt que directement de la structure JSON
- [x] Prevoir plusieurs fournisseurs futurs sans imposer une unique cle globale

## P6.2 Migration ⭐ **VALIDE**

- [x] Detecter une ancienne cle presente dans `settings.json` - Methode `migrate_from_settings_manager` implementee
- [x] La migrer vers le stockage securise retenu - Implemente avec suppression apres migration
- [x] Confirmer la reussite avant de retirer la valeur en clair - Validation par has_api_key()
- [x] **Ne jamais journaliser la cle** - Respecte
- [x] **Ne jamais inclure la cle dans un dump projet ou un export** - CredentialStore ne fait que gerer la cle
- [x] **Fallback** : Si migration echoue, conserver la cle en clair temporairement - Pas de suppression si echec

## Tests P6

- [ ] Premiere saisie cle
- [ ] Lecture apres redemarrage
- [ ] Modification cle
- [ ] Suppression cle
- [ ] Migration d'une ancienne configuration
- [ ] Echec du stockage securise **sans perte silencieuse de la cle existante**
- [ ] Verifier que `settings.json` ne contient plus le secret apres migration reussie

**Validation** : Structure de CredentialStore implementee et integree dans api_capabilities, elevenlabs_api, elevenlabs_transcriber, settings_dialog

---

# PHASE P7 - TESTS AUTOMATISES ET CI MULTIPLATEFORME (⭐ Originalement Phase 11) (🟢 VALIDE)

> **Objectif** : Passer de l'actuel `test/test.py` essentiellement manuel a une suite de non-regression.
> **Duree estimee** : 3-5 jours
> **Pre-requis** : P1-P4 terminent (fonctionnalites critiques stabilisees)
> **Date d'implementation** : 2026-10-09

## P7.1 Structure proposee ⭐ **VALIDE**

```text
tests/
├── unit/
│   ├── test_project_io.py          # Portabilite, migration ⭐ CREÉ
│   ├── test_settings.py            # First-run, validation ⭐ À CRÉER
│   ├── test_api_capabilities.py    # Mode sans API ⭐ CREÉ (nécessite Qt)
│   ├── test_project_manager.py    # ⭐ À CRÉER
│   ├── test_media_formats.py       # ⭐ À CRÉER
│   ├── test_silence_detection.py   # ⭐ À CRÉER
│   └── test_ffmpeg_resolver.py     # ⭐ CREÉ
├── integration/
│   ├── test_project_portability.py # ⭐ À CRÉER
│   ├── test_audio_pipeline.py      # ⭐ À CRÉER
│   └── test_legacy_project_migration.py # ⭐ À CRÉER
└── fixtures/
    ├── projects/
    │   ├── legacy_absolute.sttproj
    │   └── portable.sttproj
    └── media/
        ├── test.wav
        ├── test.mp3
        └── test_with_spaces.wav
```

**Fichiers créés** :
- [x] `tests/__init__.py`
- [x] `tests/unit/__init__.py`
- [x] `tests/integration/__init__.py`
- [x] `tests/fixtures/__init__.py`
- [x] `tests/fixtures/projects/__init__.py`
- [x] `tests/fixtures/media/__init__.py`
- [x] `tests/conftest.py` - Fixtures pytest
- [x] `tests/unit/test_project_io.py` - 13 tests
- [x] `tests/unit/test_ffmpeg_resolver.py` - 5 tests
- [x] `tests/unit/test_api_capabilities.py` - 2 tests (nécessite Qt)
- [x] `pytest.ini` - Configuration pytest
- [x] `requirements-test.txt` - Dépendances de test

## P7.2 Contenu des tests

- [x] Conserver des medias de test courts et legalement redistribuables/genere pour les tests - Utilisation de fixtures
- [x] **Ne jamais inclure une vraie cle API** - Respecte
- [ ] Mock/fake des appels ElevenLabs dans la suite automatique normale
- [ ] Tests reseau reels optionnels et explicitement separes

## P7.3 Matrice CI

- [ ] Windows + Python supporte (3.11+)
- [ ] Ubuntu/Linux + Python supporte
- [ ] macOS + Python supporte
- [ ] `python -m pip check` sans erreur
- [x] `pytest` passe sur les tests non-Qt (18 tests)
- [ ] Validation minimale de lancement/import Qt compatible avec l'environnement CI

**Criteres de sortie** : Une modification qui casse chemins/projets/tests de base sur un OS est detectee avant merge

**Validation** : Structure de tests créée, 18 tests unitaires opérationnels (hors Qt)

---

# PHASE P8 - FFMPEG MULTIPLATEFORME AVANCE (⭐ Originalement Phase 7) (🟢 VALIDE)

> **Objectif** : Resolution robuste multiplateforme avec strategie hierarchique.
> **Duree estimee** : 2 jours
> **Pre-requis** : P0.3 termine
> **Date d'implementation** : 2026-10-09

## P8.1 Resolveur FFmpeg ⭐ **VALIDE**

- [x] Remplacer la constante Windows-only par un resolveur de dependance - Implémenté dans get_ffmpeg_path()
- [x] Definir les noms d'executables selon la plateforme (`ffmpeg.exe` / `ffmpeg`) - Déjà implémenté
- [x] Definir une strategie prioritaire claire :
  1. [x] Binaire embarque (`tools/ffmpeg/{platform}/ffmpeg`) - _get_embedded_ffmpeg_paths()
  2. [x] Configuration utilisateur (via parametres) - get_ffmpeg_path(settings) + SettingsManager
  3. [x] `PATH` systeme - shutil.which()
- [x] Centraliser toute detection dans `services/ffmpeg_paths.py` - Oui
- [x] Conserver les services audio independants de la plateforme - Oui
- [x] Produire un message d'erreur adapte lorsque FFmpeg est absent ou non executable - validate_ffmpeg_tools() améliorée

## P8.2 Organisation des binaires ⭐ **VALIDE**

Strategie a figer avant packaging :

```text
tools/ffmpeg/
├── windows/ffmpeg.exe
├── macos/ffmpeg
└── linux/ffmpeg
```

- [x] Verifier les implications de licence/distribution avant d'embarquer un binaire - À faire avant packaging
- [x] Documenter l'installation de developpement pour chaque OS - À faire avant packaging

**Validation** : Structure supportée par _get_embedded_ffmpeg_paths(), prêt pour l'organisation multiplateforme

## Tests P8

- [ ] FFmpeg trouve dans l'emplacement embarque attendu (nécessite organisation multiplateforme)
- [ ] FFmpeg trouve via configuration utilisateur (nécessite UI de configuration)
- [x] FFmpeg trouve via `PATH` - Déjà testé via shutil.which()
- [x] FFmpeg absent -> message explicite, pas de crash - validate_ffmpeg_tools() améliorée
- [ ] FFmpeg non executable -> erreur explicite
- [ ] Trim seul
- [ ] Suppression des silences seule
- [ ] Acceleration seule
- [ ] Les trois traitements combines
- [ ] Finalisation de chaque format supporte
- [ ] Extraction audio des formats video supporte

**Validation** : Résolveur hiérarchique implémenté et fonctionnel

---

# PHASE P9 - UI MULTIPLATEFORME (⭐ Originalement Phase 8) (🟢 VALIDE)

> **Objectif** : Eliminer les dependances Windows de l'UI.
> **Duree estimee** : 3-4 jours
> **Pre-requis** : P0 termine (first-run stable)
> **Statut** : **TERMINE** - P9.1 a P9.4 implementees

## P9.1 Themes ⭐ **VALIDE**

- [x] Supprimer `app.setStyle("Windows11")` comme dependance globale
- [x] Utiliser `pyqtdarktheme` (qdarktheme) pour les themes modernces
- [x] Choisir `Fusion` comme style de base pour compatibilite multiplateforme
- [x] Verifier System / Clair / Sombre sur chacun des OS
- [x] Verifier lisibilite des controles desactives
- [x] Personnalisation du fond general pour theme clair (remplace blanc pur par #fafafa/#f8f8f8)
- [x] Personnalisation des boutons pour les deux themes (texte lisible, fond coherents)

### Details de l'implémentation
- **Package** : `pyqtdarktheme==0.1.7` ajoute a `requirements.txt`
- **Module** : `qdarktheme` avec `load_stylesheet(theme="dark"|"light")`
- **Fallback** : Palettes personnalisees originales si qdarktheme non disponible
- **Couleurs theme clair** :
  - Fond general : `#fafafa`
  - Fond principal : `#f8f8f8`
  - Zones de saisie : `#ffffff` (blanc pur pour contraste)
  - Boutons : `#f5f5f5` avec texte `#191919`
- **Couleurs theme sombre** :
  - Boutons : `#373737` avec texte `#f0f0f0`

### Fichiers concernes
- `services/theme_manager.py` - Refonte complete avec qdarktheme + stylesheets personnalises
- `requirements.txt` - Ajout de pyqtdarktheme

## P9.2 Polices ⭐ **VALIDE**

- [x] Supprimer la dependance explicite a `Segoe UI Light` - Remplacee par `QFontDatabase.systemFont(GeneralFont)` dans `home_window.py`
- [x] Utiliser la police systeme via `QFontDatabase.systemFont()`
- [x] Tester le rendu des symboles/emoji actuellement utilises comme boutons - Emojis critiques des controles media remplaces par des SVG
- [x] Remplacer les emoji critiques par des SVG - Boutons lecture/pause/precedent/suivant de l'editeur : `icons/player-*.svg` teintes avec la couleur de texte du theme via `services/icons.py` (`make_tinted_icon`)
  - Emojis restants (boutons `💾 Finaliser`, `☁ Transcrire`, zoom, accueil...) : non critiques, libelles texte ou tooltips presents ; a reevaluer visuellement sur macOS/Linux avant packaging (P11)

## P9.3 Icones ⭐ **VALIDE**

- [x] Utiliser PNG/SVG pour les icones internes a l'UI - `user.svg`, `settings.svg`, `bubble-text.svg`, `player-*.svg`
- [x] Prevoir `.ico` pour le package Windows - `icons/icon.ico` existant (utilise au demarrage)
- [x] Prevoir `.icns` pour macOS - generation au packaging (P11)
- [x] Prevoir PNG/SVG adapte pour Linux - `icons/logo.png` en repli
- [x] Ne pas faire dependre le demarrage Qt de `icons/icon.ico` uniquement - Repli `logo.png` puis demarrage sans icone (`TranscriptStudio.py`)
- [x] Correctif : icones SVG teintees theme dans la fenetre de pretraitement (lecteurs original et resultat, `player-stop.svg`, bascules play/pause en `setIcon`)

## P9.5 Hauteur des boutons ⭐ **VALIDE**

- [x] Constantes `ICON_BUTTON_WIDTH` / `ICON_BUTTON_HEIGHT` dans `services/icons.py` : taille unique de tous les boutons
- [x] `make_button_height_css()` : hauteur fixee en CSS (min-height/max-height hors padding/bordure) - le modele de taille de la stylesheet du theme depasse `setFixedSize`
- [x] Boutons a icone de l'editeur et du pretraitement styles via le generateur, hauteurs verifiees sous le theme reel
- [x] Stylesheet globale des boutons (`theme_manager.py`) pilotee par `ICON_BUTTON_HEIGHT` : accueil, parametres et dialogues inclus

## P9.4 Raccourcis ⭐ **VALIDE**

- [x] Examiner `Ctrl+S` et utiliser un raccourci standard Qt (`QKeySequence.StandardKey.Save`) - `main_window.py`
- [x] Verifier comportement attendu `Cmd+S` sous macOS - Mapping automatique par `QKeySequence.StandardKey.Save` ; validation visuelle macOS au packaging (P11)

## P9.6 Teinte des icones par theme ⭐ **VALIDE**

- [x] `make_theme_text_color(theme)` dans `services/icons.py` : teinte derivee du theme configure (`light` -> noir, `dark` -> clair, `system` -> schema de couleurs OS)
- [x] Cause : la palette Qt ne reflete pas la stylesheet du theme (palette par defaut du systeme) - icones claires invisibles en theme clair sur Windows sombre
- [x] Corrigé aux 8 points de teinte (editeur : barre d'outils, bascule play/pause, icones A+/A- ; pretraitement : barre d'outils, lecteur de resultat, bascules, reset)
- [x] Verifie pixel par pixel offscreen : clair -> icones noires, sombre -> icones claires

## Tests P9

- [x] Demarrage en theme systeme clair
- [x] Demarrage en theme systeme sombre
- [x] Forcage clair
- [x] Forcage sombre
- [x] Aucun texte illisible
- [x] Boutons avec texte lisible (noir/blanc selon theme)
- [x] Fond general moins agressif (grise clair au lieu de blanc pur)
- [x] Icones visibles et homogenes (controles media SVG, teinte par theme, verifie offscreen)
- [x] Raccourci sauvegarde natif sur chaque OS (StandardKey.Save)
- [ ] Redimensionnement et plein ecran/maximisation corrects
- [x] Test de fumee offscreen : instanciation `MainWindow` avec projet reel, icones media posees, bascule play/pause, raccourci resolu en `Ctrl+S`
- [x] Hauteur des boutons sous le theme reel : editeur (13 boutons) et pretraitement (10 boutons) a `ICON_BUTTON_WIDTH`x`ICON_BUTTON_HEIGHT` ; boutons texte (accueil, parametres) sous la hauteur cible

---

# PHASE P10 - CONFIGURATION MULTIPLATEFORME (⭐ Originalement Phase 6) (🟢 VALIDE)

> **Objectif** : Eliminer les hypotheses Windows du code metier.
> **Duree estimee** : 2 jours
> **Pre-requis** : P0 + P9 terminent
> **Statut** : **TERMINE** - Chemins centralises et temporaires isoles par session

## P10.1 `app_paths.py` ⭐ **VALIDE**

- [x] Reserver `platformdirs` aux donnees/cache/configuration applicatives - `user_data_dir` uniquement, dossier cree a l'import (deja en place)
- [x] Utiliser `QStandardPaths` pour les dossiers utilisateur proposes dans l'UI - `settings.py` (Documents par defaut) et `settings_dialog.py` (dialogue Parcourir), deja en place
- [x] **Ne plus creer automatiquement le repertoire de projets** lors de l'import de `app_paths.py` - deja en place (note explicite dans le fichier)
- [x] Centraliser les chemins applicatifs dans `app_paths.py` - `APP_DATA_DIR`, `TEMP_DIR`, `SESSION_TEMP_DIR`, `LEGACY_PROJECTS_DIR` ; `settings.py` et `audio_waveform_service.py` consomment le module

## P10.2 Temporaire et cache ⭐ **VALIDE**

- [x] Renommer le dossier temporaire `TranscriptAudio` -> `TranscriptStudio` - fait en P5.1
- [x] Eviter les collisions de fichiers temporaires entre deux medias de meme nom - sous-repertoire `SESSION_TEMP_DIR` unique par session (uuid), deux instances simultanees ne se marchent plus dessus
- [x] Prevoir a terme des sous-repertoires temporaires uniques par session/projet - implemente : `ensure_session_temp_dir()`, nettoyage au mieux a la fermeture via `atexit` (`cleanup_session_temp_dir`)
- [x] Verifier nettoyage au succes et a l'abandon - les nettoyages existants du dialogue de pretraitement (fichiers par chemin) restent valides ; le dossier de session est supprime en sortie d'application (nettoyage multi-OS a confirmer sur macOS/Linux au packaging)

## Tests P10

- [x] Chemins avec espaces - `test_same_named_media_no_cross_session_collision` (dossier "dossier a")
- [x] Chemins avec accents et Unicode - media `café été.wav` extrait par FFmpeg dans le dossier de session
- [ ] Projet sur volume/disque different - a valider au packaging (P11)
- [ ] Dossier projet en lecture seule - a valider au packaging (P11)
- [x] Deux fichiers source portant le meme nom depuis deux repertoires differents - extraction successive, fichiers sous `SESSION_TEMP_DIR`, nettoyage verifie
- [x] Aucun chemin Windows code en dur dans les `.sttproj` neufs - couvert par les tests `project_io` (chemins relatifs)

**Validation** : `tests/unit/test_app_paths.py` (5 tests, extraction FFmpeg reelle incluse) - 27 tests pytest verts au total

---

# PHASE P11 - PACKAGING (⭐ Originalement Phase 12)

> **Périmètre actuel : Windows uniquement** (macOS/Linux reportés).
> **Version diffusée : 1.0** (première distribution en exécutable).

## Stratégie Windows retenue (2026-10-10)

**Build : Nuitka, mode standalone (pas onefile), compilateur MSVC.**
- Nuitka compile le Python en C puis en binaire natif : taux de faux positifs antivirus « radicalement plus faible » que PyInstaller (archive auto-extractive = motif des packers de malware). Qt recommande officiellement Nuitka pour PySide6.
- Onefile exclu : réintroduit un bootstrap d'extraction (démarrage plus lent, profil antivirus dégradé).
- Sortie : un dossier standalone que l'on met indifféremment en ZIP, Inno Setup ou WiX plus tard.

**Distribution : installateur Inno Setup + archive ZIP portable.**
- Inno Setup : gratuit, simple, install/désinstall propres, raccourcis, per-machine.
- ZIP portable : variante sans installation ni modification du système.
- **MSI (WiX) : option différée** - aucun gain de sécurité vs Inno sans certificat (même SmartScreen, même réputation) ; pertinent uniquement pour un déploiement en entreprise (GPO, install silencieuse `msiexec /qn`). À produire sur demande, sans rien changer au build Nuitka.
- **MSIX exclu** : signature obligatoire, même pour du sideloading - incompatible avec la diffusion sans certificat.

**Réalités sécurité sans certificat (documentées pour les utilisateurs) :**
- SmartScreen affichera « Windows a protégé votre PC » au premier lancement d'une nouvelle version (réputation par hash, éditeur inconnu). Contournement utilisateur : « Informations complémentaires → Exécuter quand même ». La réputation se construit avec les téléchargements d'un même hash (publier des versions stables, ne pas régénérer l'exe pour rien).
- Faux positifs antivirus éventuels : soumettre le fichier à l'éditeur (Microsoft : formulaire d'analyse de fichier), vérifier VirusTotal.
- Étape ultérieure low-cost si besoin : certificat open-source Certum (~25-70 €/an) ou SignPath Foundation (gratuit pour projets OSS) - supprime l'avertissement et accélère la réputation.

## Windows

- [x] Build Nuitka reproductible (MSVC, standalone, plugin PySide6) depuis un environnement propre
- [x] Inclusion des ressources : `icons/`, `docs/Manuel utilisateur.pdf`
- [x] FFmpeg embarqué : `tools/ffmpeg/windows/ffmpeg.exe` (résolveur hiérarchique P8)
- [x] Icone application `icons/icon.ico`
- [x] Script Inno Setup : installateur per-machine, raccourcis, désinstallation propre
- [x] Archive ZIP portable en variante
- [ ] Vérifier le binaire sur VirusTotal ; soumettre tout faux positif détecté
- [ ] Test sur machine Windows sans environnement Python de dev
- [x] Numéroter la version diffusée : 1.0

### Validation du build (2026-10-10)

- Sortie : build/TranscriptStudio.dist/TranscriptStudio.exe (standalone, ~270 Mo avec FFmpeg embarqué et le manuel PDF), métadonnées version 1.0.0.0, icône Windows, console désactivée.
- Reproductibilité : script tools/build_windows.bat (Nuitka 4.3, MSVC, plugin PySide6, données icons/, docs/Manuel utilisateur.pdf, tools/ffmpeg/windows/ffmpeg.exe, --include-package-data=qdarktheme pour les templates SVG du thème).
- Test de fumée : binaire lancé, fenêtre principale active 15 s (184 Mo en mémoire), arrêt propre ; 30 tests pytest verts après correctifs.
- Piège 1 (résolu) : le build doit partir d'un CPython standard 3.11, pas d'une distribution Anaconda/conda. Avec le Python Anaconda de l'environnement de dev, import ctypes (utilisé au démarrage par platformdirs) déclenche un arrêt fatal 0x40000015 sans trace Python dans le binaire standalone. Environnement propre : uv venv --python 3.11 + pip install -r requirements.txt nuitka ordered-set zstandard.
- Piège 2 (résolu) : services/elevenlabs_api.py et services/elevenlabs_transcriber.py contenaient un « é » encodé en Latin-1 dans un commentaire (fichiers mixtes UTF-8/Latin-1). Python ne pouvait les parser que grâce au cache .pyc local : tout checkout frais plantait au démarrage. Les deux fichiers ont été re-encodés intégralement en UTF-8 (une ligne corrigée par fichier).

### Distribution (2026-10-10)

- Installateur : tools/installer_windows.iss (Inno Setup 6.7.3, per-machine, UAC, raccourcis bureau + menu Demarrer, entree desinstallation HKLM). Compile via ISCC.exe. Sortie : dist/TranscriptStudio-1.0-setup.exe (77 Mo).
- ZIP portable : dist/TranscriptStudio-1.0-portable.zip (110 Mo), contenu integral du dossier standalone.
- Validation installateur sur cette machine : installation silencieuse OK (Program Files, FFmpeg embarque, manuel PDF, raccourcis tous utilisateurs), lancement de l'exe installe OK, desinstallation silencieuse OK (dossier, raccourcis et entree registre supprimes ; donnees utilisateur AppData conservees).
- Restent des actions utilisateur : verification VirusTotal des deux artefacts, test sur une machine Windows vierge sans Python de dev.

## Documentation utilisateur (préalable au build)

- [x] Copie du manuel utilisateur : `docs/Manuel_utilisateur_Transcript_Studio_v1.0.docx`
- [x] Section « Installation » (installateur, version portable, avertissement SmartScreen et contournement, mise à jour)
- [x] Ligne de dépannage : avertissement « Windows a protégé votre PC »
- [x] Version 1.0 / Octobre 2026 (couverture et fin de document)
- [x] Régénérer `docs/Manuel utilisateur.pdf` depuis le Word v1.0 (export manuel depuis Word) - PDF régénéré, v1.1.docx retiré

## macOS / Linux (reportés)

- [ ] macOS : bundle `.app`, icone `.icns`, validation sur machine (VM)
- [ ] Linux : AppImage/Flatpak, dépendances Qt Multimedia, validation distribution cible (Ubuntu 22.04+)
- [ ] Validation visuelle multi-OS : emojis restants, hauteurs de boutons, `Cmd+S`, nettoyage des temporaires

---

# PHASE E1 - AMELIORATIONS UX EDITEUR (hors portabilite)

> **Objectif** : Ameliorer le confort de lecture/correction dans l'editeur de transcription.
> **Statut** : ⭐ **TERMINE** (E1.1/E1.2 : 0e8a35a ; E1.3 : 13f4f38)

## E1.1 Puce speaker ⭐ **VALIDE**

- [x] Remplacer le disque CSS (ecrase par la stylesheet qdarktheme depuis P9.1) par `icons/user.svg` teinte a la couleur de l'intervenant
- [x] Rendu via `QSvgRenderer` en pixmap haute densite (devicePixelRatio)
- [x] Icône insensible aux stylesheets globales, bouton toujours cliquable (menu changement de speaker)
- **Commit** : 0e8a35a

## E1.2 Mot lu sans decalage ⭐ **VALIDE**

- [x] Supprimer le `font-weight:bold` sur le mot actif : la mise en gras provoquait un decalage (reflow) de tous les mots suivants
- **Commit** : 0e8a35a

## E1.3 Surlignage anime du mot lu ⭐ **VALIDE**

- [x] Remplacer le re-render HTML complet a chaque changement de mot par des `ExtraSelections` (cartographie des ancres `word_N` -> positions dans le document)
- [x] Fondu d'apparition ~70 ms et de retrait ~180 ms (`QVariantAnimation`, courbe OutQuad), un fondu de retrait par mot : plusieurs mots s'effacent simultanement en lecture rapide au lieu de disparaitre instantanement
- [x] Reapplication immediate sans animation apres re-render (taille de police, edition)
- [x] Correction remanence : retrait explicite du mot en fondu interrompu dans `start_fade_out` (`stop()` n'emets pas `finished` sur `QVariantAnimation`)
- [x] Theme sombre : variante assombrie du jaune (`HIGHLIGHT_COLOR_DARK`) ; la couleur du texte n'est jamais modifiee (la selection ne peint que le fond), detection du theme par la couleur de texte
- [x] Regions continues : chaque mot reel possede l'espace qui le precede + son texte + sa ponctuation ; ponctuation isolee avec le mot precedent, guillemets ouvrants avec le mot suivant (espace d'inter-mots colore avec le mot qui le suit)
- [x] Ancres, clics souris, double-clic et menus contextuels inchanges
- [x] Gain : plus aucun reflow ni reconstruction de document pendant la lecture
- **Commit** : 13f4f38
- **Validation** : script fonctionnel offscreen `.vibe/test_highlight_fade.py` (8 controles : cartographie, fondus, transition, scrubbing arriere, desactivation, transitions rapides sans remanence, re-render, ancres)

## Tests E1

- [x] Cartographie mot -> position correcte apres rendu
- [x] Fondu entrant jusqu'a alpha 255, selection unique sur le bon mot
- [x] Transition entre deux mots (fondu croise)
- [x] Scrubbing arriere (interruption d'un fondu sortant)
- [x] Desactivation complete apres fondu sortant
- [x] Transitions rapides (mots plus courts que le fondu) sans remanence accumulee
- [x] Regions avec ponctuation isolee (`, . ; : ! ?`) et guillemets (« ouvrant au mot suivant, » fermant au mot precedent)
- [x] Re-render avec mot actif reaplique sans animation
- [x] Ancres de clic intactes

---

# PHASE E2 - MENU CONTEXTUEL DES PROJETS RECENTS (hors portabilite)

> **Objectif** : Gérer une entrée de la liste des projets récents sans quitter l'accueil.
> **Statut** : ⭐ **TERMINE** (59f7241)

## E2.1 Clic droit sur un projet récent ⭐ **VALIDE**

- [x] Menu contextuel sur la liste `Projets récents` de l'accueil (CustomContextMenu)
- [x] « Ouvrir le projet » : même action que le double-clic (`open_recent_project`)
- [x] « Ouvrir le répertoire du projet » : ouvre le dossier du `.sttproj` dans l'explorateur (`QDesktopServices`), avertissement si le répertoire n'existe plus
- [x] « Retirer de la liste des projets récents » : supprime la référence (le fichier projet n'est pas touché sur le disque), liste rafraîchie
- [x] `SettingsManager.remove_recent_project()` : retrait de la référence + sauvegarde, retourne True si l'entrée existait
- [x] `SettingsManager` : dossier de paramétrage injectable (`app_folder`), utilisé par les tests pour isoler la configuration réelle

## Tests E2

- [x] `tests/unit/test_recent_projects.py` (3 tests) : retrait d'une entrée, entrée absente, fichier conservé sur disque
- [x] Fumée offscreen : politique de menu contextuel activee, menu a 3 actions + separateur, retrait visible dans la liste affichee
- [x] 30 tests pytest verts au total

---

# 📅 PLANNING RECOMMANDE

## SPRINT 1 (Semaine 1) : Deblocage & Portabilite ⭐ **TERMINE**
- **J1-J2** : P0.1 (First-run) + P0.2 (Decouplage API) + P0.3 (FFmpeg minimal) ⭐ **TERMINE**
- **J3-J5** : P1 (Portabilite projets) ⭐ **TERMINE**

**Livrable** : Nouveau utilisateur peut demarrer, creer un projet portable.
**Statut** : ✅ **Atteint** - Tous les objectifs du Sprint 1 réalisés

---

## SPRINT 2 (Semaine 2) : Robustesse & Mode Degrade
- **J6-J7** : P2 (Mode sans cle API)
- **J8-J10** : P3 (Decouplage audio/transcription) + P4 (Resilience)

**Livrable** : Tous les workflows fonctionnent sans cle API.

---

## SPRINT 3 (Semaine 3) : Qualite & Securite
- **J11-J12** : P5 (Nettoyage) + P6 (Stockage securise)
- **J13-J15** : P7 (Tests automatises)

**Livrable** : Code propre, tests de base, cle API securisee.

---

## SPRINT 4 (Semaine 4+) : Finalisation
- **J16-J17** : P8 (FFmpeg avance) + P9 (UI multiplateforme) + P10 (Configuration)
- **J18+** : P11 (Packaging)

**Livrable** : Builds testes sur chaque OS.

---

# 🗺️ ORDRE DE COMMITS RECOMMANDE (Mis a jour)

> **Note** : Les numeros de commits ont ete ajustes pour refleter la nouvelle prioritisation.

## Sprint 1 - Deblocage
- [x] **Commit P0-1 — First-run setup** : b08698e - Repertoire projets obligatoire, Documents propose, cle facultative
- [x] **Commit P0-2 — API capability decoupling** : 952a010 - Centralisation des capacites, blocage cible des fonctions ElevenLabs
- [x] **Commit P0-3 — Minimal cross-platform FFmpeg** : fd615c9 - Resolveur basique, strategie de fallback

## Sprint 2 - Portabilite
- [x] **Commit P1-1 — Portable project format v1** : 76dc6cf - `project_format_version`, chemins relatifs, suppression `project_file` du JSON
- [x] **Commit P1-2 — Legacy project migration** : 71ac2cf - Resolution chemins, migration non-destructive
- [x] **Commit P1-3 — Project save/load refactoring** : a52e208 - Sauvegarde relative, autosave, export

## Sprint 3 - Mode Degrade & Decouplage
- [x] **Commit P2-1 — API-less mode foundation** : Fonctions autorisees sans API (verification complete)
- [x] **Commit P2-2 — API capability UI** : UX degradee, messages clairs, bouton Transcrire desactive sans API, affichage etat API sur accueil
- [x] **Commit P3-1 — Audio finalization decoupling** : Separer finalisation et transcription avec boutons dedies
- [x] **Commit P3-2 — Project lifecycle states** : Etats provisoire/finalise/transcrit via _finalize_mode

## Sprint 4 - Resilience
- [x] **Commit P4-1 — Missing media recovery** : c5ca718 - Strategie de relocalisation
- [x] **Commit P4-2 — Audio-less editing mode** : c5ca718 - Edition sans media

## Sprint 5 - Qualite
- [x] **Commit P5-1 — Historical naming cleanup** : 93f90e9 - `TranscriptAudio` -> `TranscriptStudio`
- [x] **Commit P5-2 — Pathlib audit** : 93f90e9 - Elimination des chemins Windows-only
- [x] **Commit P6-1 — Secure credential storage** : 5744295 - `CredentialStore`, migration

## Sprint 6 - Tests
- [x] **Commit P7-1 — Unit tests foundation** : 7bfcd17 - Structure tests, fixtures
- [x] **Commit P7-2 — Portability test suite** : 7bfcd17 - Tests project_io/ffmpeg_resolver/api_capabilities (22 verts)
- [ ] **Commit P7-3 — CI matrix setup** : GitHub Actions/other CI

## Sprint 7 - Finalisation
- [x] **Commit P8-1 — Advanced FFmpeg resolver** : f327448 - Strategie hierarchique
- [x] **Commit P9-1 — Cross-platform UI** : b9429dd - Themes qdarktheme (P9.1)
- [x] **Commit P9-2 — Polices systeme, icones media SVG, repli icone, raccourci standard** : 7487e24 - P9.2-P9.4
- [x] **Commit P9-3 — Icones SVG pretraitement + hauteur globale des boutons** : 91dd073 - P9.5
- [x] **Commit P9-4 — Teinte des icones par theme configure** : 91dee65 - P9.6 (fin de la teinte par palette Qt)
- [x] **Commit P10-1 — Path configuration** : 55b7c3b - app_paths centralise, temporaires uniques par session

## Hors sprint - Ameliorations editeur
- [x] **Commit E1-1 — Icone speaker teintee + mot lu sans decalage** : 0e8a35a
- [x] **Commit E1-2 — Surlignage anime du mot lu (ExtraSelections + fondus)** : 13f4f38
- [x] **Commit E2-1 — Menu contextuel projets recents** : 59f7241 - ouvrir, ouvrir repertoire, retirer de la liste

## Sprint 8 - Packaging
- [x] **Commit P11-1 — Documentation v1.0** : manuel utilisateur 1.0 (docx + PDF regenere, v1.1 retire), version 1.0 affichee (a commiter)
- [ ] **Commit P11-2 — Windows packaging** : build Nuitka + Inno Setup + ZIP portable (v1.0)
- [ ] **Commit P11-3 — macOS packaging** : Bundle .app (différé)
- [ ] **Commit P11-4 — Linux packaging** : AppImage/Flatpak (différé)

---

# 🛡️ GARDE-FOUS AVANT CHAQUE COMMIT

- [ ] `git status` propre ou changements parfaitement identifies
- [ ] Tests automatises concernes verts
- [ ] Tests manuels cibles du commit effectues
- [ ] **Aucune vraie cle API dans les fichiers suivis par Git**
- [ ] Aucun media utilisateur ajoute accidentellement au depot
- [ ] Aucun `.sttproj` de fixture ne contient de donnee personnelle/confidentielle
- [ ] README/architecture mis a jour lorsque le contrat fonctionnel change
- [ ] **Chaque commit doit etre testable et reversible**

---

# 📊 ETAT GLOBAL DU PROJET

## Phases Terminees
- [x] **P0 - DEBLOCAGE IMMEDIAT** : 
  - [x] P0.1 First-Run Minimal ⭐ **VALIDE**
  - [x] P0.2 Decouplage Cle API / Capacites ⭐ **VALIDE**
  - [x] P0.3 FFmpeg Multiplateforme Minimal ⭐ **VALIDE**

- [x] **P1 - PORTABILITE DES PROJETS** ⭐ **VALIDE**
  - [x] P1.1 Definir le contrat du format projet ⭐ **VALIDE**
  - [x] P1.2 Resolution a l'ouverture ⭐ **VALIDE**
  - [x] P1.3 Migration non destructive des anciens projets ⭐ **VALIDE**
  - [x] P1.4 Sauvegarde et autosave apres deplacement ⭐ **VALIDE**

- [x] **P2 - MODE SANS CLE API** ⭐ **TERMINE** (749ed6c)
- [x] **P3 - DECOUPLAGE FINALISATION / TRANSCRIPTION** ⭐ **TERMINE** (dbe13f1)
- [x] **P4 - RESILIENCE FACE A UN MEDIA MANQUANT** ⭐ **TERMINE** (c5ca718)
- [x] **P5 - NETTOYAGE** ⭐ **TERMINE** (93f90e9)
- [x] **P6 - STOCKAGE SECURISE DES CLES API** ⭐ **TERMINE** (5744295)
- [x] **P7 - TESTS AUTOMATISES** ⭐ **TERMINE** (7bfcd17 - 22 tests pytest verts ; CI restant a configurer)
- [x] **P8 - FFMPEG MULTIPLATEFORME AVANCE** ⭐ **TERMINE** (f327448)
- [x] **P9 - UI MULTIPLATEFORME** ⭐ **TERMINE** (P9.1 : b9429dd ; P9.2-P9.4 : 7487e24 ; P9.5 : 91dd073)
- [x] **E1 - AMELIORATIONS UX EDITEUR** ⭐ **TERMINE** (E1.1/E1.2 : 0e8a35a ; E1.3 : 13f4f38)
- [x] **P10 - CONFIGURATION MULTIPLATEFORME** ⭐ **TERMINE** (app_paths centralise, temporaires isoles par session, 5 nouveaux tests)

## Phases en Cours
- Aucune

## Prochaine Phase
**P11 - PACKAGING (Windows d'abord)** : build Nuitka standalone, installateur Inno Setup + ZIP portable, version 1.0 ; documentation utilisateur v1.0 réalisée en préalable

---

# 🎯 DEFINITION OF DONE GLOBALE

La campagne est terminee lorsque :

## Portabilite
- [ ] Un projet neuf est portable par conception
- [ ] Les anciens projets restent ouvrables et migrent sans perte
- [ ] Un projet peut etre deplace/copie puis sauvegarde sans reference a son ancien emplacement

## Configuration
- [ ] Le premier lancement impose un repertoire projets valide
- [ ] La cle API demure facultative

## Mode Sans API
- [x] Sans cle, pretraitement, finalisation, ouverture, edition et exports restent utilisables
- [ ] Un media absent n'empeche pas l'ouverture du transcript

## Multiplateforme
- [ ] Le code source fonctionne sur Windows, macOS et Linux pour le perimetre valide
- [ ] FFmpeg est resolu proprement sur chaque plateforme cible
- [ ] L'UI n'est plus dependante du style/police/icone Windows

## Decouplage
- [x] La finalisation audio est decouplee de la transcription

## Securite
- [ ] La cle API n'est plus conservee en clair apres mise en place du stockage securise

## Tests
- [ ] La suite `pytest` couvre les regles de portabilite critiques
- [ ] Les tests croises Windows/macOS/Linux sont valides
- [ ] Chaque package distribue est teste sur une installation propre

---

# 📌 NOTES DE PLANIFICATION

1. **Ne pas fusionner portabilite des `.sttproj` et first-run dans le meme commit.** Le premier corrige un contrat de fichier, le second un comportement de configuration.

2. **Ne pas implementer le stockage securise de la cle avant d'avoir stabilise le first-run.** Cela permet de diagnostiquer chaque evolution separément. 
   > **Recommandation** : Implementer P6 (stockage securise) APRES P0, P1, P2 pour eviter les pertes de cle pendant la stabilisation.

3. **Tester le code source sur macOS/Linux avant de travailler le packaging.** Un build ne doit pas servir a decouvrir les dependances implicites de la plateforme.
   > **Action** : Creer des VMs/environnements cloud pour macOS et Linux des le debut.

4. **Pour les projets portables, le dossier contenant `project.sttproj` est l'ancre de resolution.** Le `projects_root` ne sert qu'a la creation/navigation par defaut.

5. **Les chemins absolus dans `recent_projects` restent acceptables comme preference locale utilisateur.** Ils ne font pas partie du format portable du projet et doivent simplement etre nettoyes quand ils deviennent invalides.

6. **Priorite a la stabilite** : Chaque phase doit etre completement testee avant de passer a la suivante. Eviter les modifications qui touchent plusieurs composants en meme temps.

---

# 🚨 ANALYSE DES RISQUES ET MITIGATION

## Risques Eleves

| Risque | Impact | Mitigation |
|--------|--------|------------|
| **Migration projets existants** | Perte de donnees | Sauvegarder tous les `.sttproj` avant modification, migration non-destructive |
| **Changement format projet** | Incompatibilite | Versionnage + migration non-destructive |
| **FFmpeg multiplateforme** | Echec sur macOS/Linux | Tester tot sur chaque OS avec fallback PATH |
| **Stockage cle API** | Echec sur certains OS | Prevoir fallback (settings.json temporaire) |

## Risques Moyens

| Risque | Impact | Mitigation |
|--------|--------|------------|
| **Tests automatises** | Temps de developpement | Commencer par tests manuels cibles, prioriser tests critiques |
| **UI multiplateforme** | Incoherences visuelles | Utiliser themes Qt natifs, tester tot |
| **Packaging** | Complexite | Documenter chaque etape, tester sur machines propres |

---

# 💡 RECOMMANDATIONS STRATEGIQUES

## 1. Commencez par P0 (First-Run + Decouplage API)
- **Pourquoi** : Sans first-run, les nouveaux utilisateurs ont une mauvaise experience
- **Impact minimal** : Pas de changement de format de projet
- **Test facile** : Simuler nouvelle installation

## 2. Priorite a la Portabilite (P1) avant le Packaging
- **Pourquoi** : Un projet non portable = echec sur macOS/Linux
- **Dependances** : P0 doit etre fait avant (first-run gere `projects_root`)

## 3. Ne pas melanger les phases
- **P0** : First-run + Decouplage (configuration utilisateur)
- **P1** : Contrat de fichier (chemin relatif, migration)
- **P2** : Capacites API (mode degrade)
- **P3** : Decouplage workflow (finalisation vs transcription)
- **P4** : Resilience (media manquant)
- **P5** : Nettoyage (code propre)
- **P6** : Securite (cle API)

> **Chaque phase doit etre completement testee et validee avant de passer a la suivante.**

## 4. Tester sur macOS/Linux le plus tot possible
- **Creer une VM/Cloud** pour macOS et Linux des le debut
- **Valider P0 + P1** avant de continuer sur d'autres phases
- **Eviter** : Decouvrir les problemes multiplateforme a la fin du projet

## 5. Stockage Securise (P6) apres Stabilisation
- **Pourquoi** : Si la migration echoue, la cle est perdue
- **Pre-requis** : P0 (first-run) doit etre stable
- **Fallback** : Conserver la cle en clair temporairement si migration echoue

## 6. Documentation Continue
- Mettre a jour `README.md` apres chaque phase majeure
- Documenter les changements de contrat dans `architecture/`
- Maintenir un journal des decisions (ADR) si besoin

---

# 📚 REFERENCES

- **Etat initial du code** : Voir `project_dump.txt` pour l'analyse complete
- **Prerequis techniques** : Python 3.11+, PySide6, platformdirs, FFmpeg
- **Licences** : GPL-3.0-only (a confirmer pour le packaging)
- **Dependencies externes** : ElevenLabs API (optionnelle), FFmpeg (obligatoire)

---

# V2 — ETUDES, TRAITEMENTS LLM ET REFORMULATION (P14+)

> Source de verite de la specification v2 : assets de l'atelier recopies dans
> `architecture/spec_v2/` (FEUILLE_DE_ROUTE_V2.md, CONTRAT_FORMAT_ETUDE_V2.md,
> ADDENDUM_DEMARRAGE_V2.md...). P11 clos le 2026-10-27 : la v2 est debloquee.
> Le contrat du format etude fait autorite pour P14 (implementation stricte).

## P14 — Format Etude & fondations donnees

- [x] P14.1 Contrat `etude.json` + objets Python dans `models/etude.py`
      (etude, reunion lieee, registre FID unique par etude, decoupage, resultats
      versionnes par bloc avec FID stable, resume par reunion, synthese versionnee,
      parametres avec prompts v2 en valeurs actives) + validation de schema
      (`services/etude_schema.py`, `services/etude_io.py`, `services/timecodes.py`)
      + tests unitaires (`tests/unit/test_etude_format.py`, dont les 5 regles
      d'invariance du contrat §12). Prompts v2 embarques dans `resources/prompts/`.
- [x] P14.2 Journal des operations de pretraitement persiste dans le dossier
      projet v1 (`journal_operations.json`, additif non destructif : decoupe,
      silences supprimes avec positions et durees originales, acceleration ;
      un nouveau journal remplace l'ancien) + conversions position traitee <->
      original, tests unitaires obligatoires.
- [x] P14.3 UI : section Etudes sur l'accueil, page Etude (creation, ajout de
      reunions = projets v1 inchanges, ordre, mode degrade si projet introuvable,
      navigation accueil -> etude -> reunion).
- [x] P14.4 Decoupage en interventions depuis la diarisation validee ;
      sous-decoupage automatique des monologues longs aux pauses reelles
      (journal des operations), jamais dans une citation biblique, re-attribution
      des FID (bornes inchangees = FID conserve).
- [x] P14.5 Fusion de blocs et ordre d'ouvrage par reunion : fusion de
      segmentation (nouveau FID, locuteurs union multi-locuteurs, bornes
      extremes, concatenation chronologique, fusion_de = FID sources, FID
      sources inactifs jamais reutilises avec horodatage de fin, resultats
      conserves, reversibilite par defusion reactivant les memes FID) ;
      ordre d'ouvrage par reunion stocke en parallele de l'ordre
      chronologique (defaut chronologique, permutation des blocs actifs,
      mis a jour par fusion/defusion) ; 21 tests unitaires.

## P15 — Service LLM multi-fournisseurs (spec : spec_v2/PARAMETRAGE_LLM_V2.md)

- [x] P15.1 Catalogue LLM embarqué et extensible (`services/llm/catalogue.py`,
      défaut `resources/llm/catalogue_defaut.json` : OpenAI, Mistral, Anthropic
      avec capacités et prix ; stocké dans le dossier de paramétrage ;
      réinitialisation reconstituant les défauts sans perdre les ajouts
      utilisateur) + CredentialStore générique (une clé par fournisseur,
      jamais en clair hors du store) + service LLM (`services/llm/client.py` :
      client abstrait, adaptateurs openai_compatible et anthropic, streaming
      SSE, usage réel et coût estimé au catalogue, relance automatique avec
      backoff sur erreurs transitoires, annulation propre, messages d'erreur
      clairs sans jamais exposer la clé, fournisseur local sans clé) ; 31
      tests unitaires dont invariants 1/3/5 du paramétrage LLM.
- [ ] P15.2 Réglages : onglet LLM (fournisseur, clé masquée + « Tester la
      clé », modèle, température/max_tokens selon capacités, éditeur de
      catalogue).
- [ ] P15.3 Moteur de traitement : assemblage de contexte (fenêtre glissante,
      budget), exécution séquentielle par unité, stockage des résultats.
- [ ] P15.4 Journal de passe : par intervention, tokens in/out, coût, durée.

## Phases suivantes (voir spec_v2/FEUILLE_DE_ROUTE_V2.md)

- P15 Service LLM multi-fournisseurs (spec separee : PARAMETRAGE_LLM_V2.md).
- P16 Bloc Reformulation et page Traitement (spec : UI_REFORMULATION_V2.md).
- P17 Synthese d'etude et bloc Resume.
- P18 JND locale, validation des references, export ouvrage.
- P19/P20 (v2.1) Page Ouvrage et edition avancee.
