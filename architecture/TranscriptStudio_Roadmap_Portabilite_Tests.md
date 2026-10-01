# Transcript Studio — Roadmap portabilité, configuration et robustesse projets

> Document de travail basé sur l'état du code fourni dans `project_dump.txt`.  
> Objectif : corriger la portabilité des projets, instaurer une configuration initiale explicite, permettre un fonctionnement utile sans clé API, préparer Windows/macOS/Linux et sécuriser progressivement la configuration.

## 0. Principes directeurs

- [ ] Un dossier de projet doit pouvoir être déplacé sans casser son ouverture.
- [ ] Un même projet doit pouvoir être transféré entre Windows, macOS et Linux.
- [ ] Aucun chemin absolu propre à une machine ne doit être nécessaire dans un `.sttproj` portable.
- [ ] `project_file` reste une information d'exécution en mémoire, pas une donnée persistée dans le projet.
- [ ] Le répertoire racine des projets est choisi explicitement par l'utilisateur au premier lancement.
- [ ] `Documents/Projets Transcript Studio` est proposé, jamais imposé silencieusement.
- [ ] La clé ElevenLabs est facultative pour démarrer l'application.
- [ ] Sans clé API, seules les fonctions nécessitant réellement ElevenLabs sont indisponibles.
- [ ] Le prétraitement et la finalisation audio doivent pouvoir fonctionner sans lancer une transcription.
- [ ] Les particularités Windows/macOS/Linux doivent être centralisées et non dispersées dans l'UI ou le métier.
- [ ] Chaque étape fait l'objet d'un commit isolé, testable et réversible.

---

# Phase préalable — Sécurisation du dépôt et renommage du dossier de développement

## P0.1 État de référence Git

- [ ] Exécuter `git status` et vérifier qu'aucune modification non souhaitée n'est présente.
- [ ] Committer ou mettre de côté les modifications légitimes en cours.
- [ ] Créer si souhaité un tag/point de restauration avant chantier.
- [ ] Noter la branche de travail actuelle.

## P0.2 Renommage du dossier local

Cible recommandée : `TranscriptStudio_Dev`.

- [ ] Fermer Transcript Studio.
- [ ] Fermer les terminaux dont le répertoire courant est le dépôt.
- [ ] Fermer VS Code ou rouvrir ensuite le nouveau dossier.
- [ ] Renommer uniquement le dossier contenant le dépôt : `TranscriptAudio` → `TranscriptStudio_Dev`.
- [ ] Ne pas renommer ni déplacer le dossier interne `.git`.
- [ ] Rouvrir le dépôt depuis son nouvel emplacement.
- [ ] Vérifier `git status`.
- [ ] Vérifier `git branch`.
- [ ] Vérifier `git remote -v`.

## Tests P0

- [ ] L'historique Git est toujours visible.
- [ ] La branche active est inchangée.
- [ ] Le remote est inchangé.
- [ ] Aucun fichier n'apparaît supprimé/recréé uniquement à cause du renommage du dossier parent.
- [ ] `python TranscriptStudio.py` démarre encore depuis le nouveau chemin.

**Critère de sortie :** le dépôt fonctionne depuis `TranscriptStudio_Dev` avant toute modification fonctionnelle.

---

# Phase 1 — Projets portables et migration du format `.sttproj`

## Objectif

Corriger le bug actuel : un projet copié ou déplacé doit continuer à retrouver son audio et à sauvegarder au nouvel emplacement.

## Fichiers principalement concernés

- `services/project_io.py`
- `models/project.py`
- `ui/home_window.py`
- `ui/main_window.py`
- éventuellement nouveau service `services/project_paths.py`

## P1.1 Définir le contrat du format projet

- [ ] Ajouter un numéro de version de format, par exemple `project_format_version`.
- [ ] Définir que `audio_file` est persisté relativement au répertoire contenant `project.sttproj` lorsque l'audio appartient au projet.
- [ ] Utiliser un chemin JSON canonique avec `/` pour les références relatives.
- [ ] Ne plus écrire `project_file` dans les nouveaux `.sttproj`.
- [ ] Conserver `Project.project_file` en mémoire pour sauvegarde, autosave, titre et export.
- [ ] Définir explicitement le comportement pour un média externe au dossier projet.

### Choix recommandé pour les nouveaux projets

- [ ] Copier le média dans le dossier projet comme aujourd'hui.
- [ ] Enregistrer seulement son chemin relatif.
- [ ] Éviter les références permanentes à des médias externes pour les nouveaux projets.

## P1.2 Résolution à l'ouverture

- [ ] Dans `load_project(filename)`, fixer systématiquement `project.project_file = Path(filename).resolve()`.
- [ ] Si `audio_file` est relatif, le résoudre depuis `Path(filename).parent`.
- [ ] Si `audio_file` est absolu et existe, accepter l'ancien projet tel quel en mémoire.
- [ ] Si l'ancien chemin absolu n'existe plus, rechercher dans le dossier actuel du projet un fichier de même nom.
- [ ] Ne jamais résoudre un média relativement au `projects_root` global.
- [ ] Normaliser avec `pathlib`.

## P1.3 Migration non destructive des anciens projets

- [ ] L'ouverture d'un ancien projet ne doit pas modifier immédiatement le fichier sur disque.
- [ ] À la prochaine sauvegarde, convertir `audio_file` en relatif si l'audio se trouve dans le dossier projet.
- [ ] Supprimer alors `project_file` du JSON écrit.
- [ ] Conserver toutes les données de transcription existantes sans régression.
- [ ] Conserver la logique de réparation des anciens `speaker_id`.

## P1.4 Sauvegarde et autosave après déplacement

- [ ] Vérifier que `Ctrl+S` sauvegarde dans le `.sttproj` effectivement ouvert.
- [ ] Vérifier que l'autosave écrit au nouvel emplacement et jamais dans l'ancien dossier.
- [ ] Vérifier que l'export propose le dossier du `.sttproj` effectivement ouvert.
- [ ] Vérifier que le titre de l'éditeur utilise le dossier courant.

## Tests automatisés P1

Créer des tests `pytest` sans dépendre de l'UI :

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

- [ ] Créer un projet neuf et transcrire un petit audio.
- [ ] Fermer l'application.
- [ ] Copier tout le dossier projet ailleurs.
- [ ] Ouvrir le `.sttproj` copié.
- [ ] Vérifier lecture audio, durée, timeline et synchronisation.
- [ ] Modifier un mot, sauvegarder, fermer et rouvrir.
- [ ] Vérifier que l'ancien dossier n'a pas été touché.
- [ ] Vérifier le contenu JSON du nouveau `.sttproj`.
- [ ] Répéter avec un projet ancien contenant un chemin absolu devenu invalide.

**Critère de sortie :** déplacement intégral d'un dossier projet = ouverture, lecture, édition, sauvegarde et export fonctionnels.

---

# Phase 2 — Configuration initiale obligatoire

## Objectif

Au premier lancement, imposer le choix/validation d'un répertoire projets. La clé API reste facultative.

## Fichiers concernés

- `TranscriptStudio.py`
- `services/app_paths.py`
- `services/settings.py`
- `ui/settings_dialog.py`

## P2.1 État de première utilisation

- [ ] Ajouter `initial_setup_completed: false` aux paramètres par défaut.
- [ ] Ne pas considérer l'absence de clé API comme une configuration incomplète.
- [ ] Ajouter `is_initial_setup_completed()`.
- [ ] Ajouter une validation atomique de fin de configuration.

## P2.2 Répertoire proposé

- [ ] Utiliser `QStandardPaths.DocumentsLocation` pour obtenir le dossier Documents natif.
- [ ] Proposer `<Documents>/Projets Transcript Studio`.
- [ ] Ne pas créer automatiquement un `Projects` utilisateur dans AppData.
- [ ] Conserver AppData uniquement pour les données internes/configuration.
- [ ] Permettre la sélection de n'importe quel répertoire accessible en écriture.

## P2.3 Validation du répertoire

- [ ] Refuser une valeur vide.
- [ ] Créer le dossier proposé/choisi si nécessaire après validation explicite.
- [ ] Vérifier que le chemin est un répertoire.
- [ ] Vérifier les droits d'écriture par un test contrôlé, puis nettoyer le fichier de test.
- [ ] Afficher une erreur claire si le dossier est inutilisable.
- [ ] Ne marquer `initial_setup_completed = true` qu'après succès.

## P2.4 Mode `first_run` du dialogue Paramètres

- [ ] Réutiliser `SettingsDialog` avec un mode de configuration initiale.
- [ ] Afficher clairement que le répertoire projets est obligatoire.
- [ ] Afficher clairement que la clé ElevenLabs est facultative.
- [ ] Remplacer `Annuler` par `Quitter` lors du premier lancement.
- [ ] Intercepter la fermeture `X` : configuration incomplète → fermeture de l'application.
- [ ] En usage normal, conserver `Enregistrer / Annuler`.

## P2.5 Compatibilité installations existantes

- [ ] Si un `settings.json` existant contient déjà `projects_root`, ne pas le déplacer silencieusement.
- [ ] Définir la migration de `initial_setup_completed` pour un utilisateur existant.
- [ ] Recommandation : considérer la configuration existante comme complète si `projects_root` est valide, sinon ouvrir le first-run.
- [ ] Ne supprimer ni déplacer aucun projet existant automatiquement.

## Tests automatisés P2

- [ ] `test_default_settings_first_run_false`
- [ ] `test_documents_suggestion_is_not_appdata`
- [ ] `test_first_run_requires_projects_root`
- [ ] `test_first_run_accepts_missing_api_key`
- [ ] `test_first_run_rejects_unwritable_project_root`
- [ ] `test_existing_valid_settings_are_migrated_without_moving_projects`
- [ ] `test_existing_invalid_projects_root_requires_configuration`

## Tests manuels P2

- [ ] Simuler installation neuve en isolant/supprimant le `settings.json` de test.
- [ ] Vérifier ouverture automatique des Paramètres.
- [ ] Vérifier chemin Documents proposé.
- [ ] Valider sans clé API.
- [ ] Relancer : la fenêtre first-run ne doit plus apparaître.
- [ ] Refaire le test avec un chemin personnalisé.
- [ ] Tester un répertoire non accessible en écriture.
- [ ] Tester un chemin contenant espaces, accents et caractères Unicode valides.

**Critère de sortie :** aucun nouvel utilisateur n'accède à l'accueil avant d'avoir validé un répertoire projets utilisable.

---

# Phase 3 — Mode sans clé API et gestion des capacités

## Objectif

Transcript Studio doit rester utile sans clé ElevenLabs.

## P3.1 Centraliser la notion de capacité

- [ ] Ajouter une méthode/service `has_transcription_api()` ou équivalent.
- [ ] Éviter les tests `if api_key` dispersés dans toute l'application.
- [ ] Distinguer capacité locale et capacité en ligne.

## P3.2 Fonctions autorisées sans API

- [ ] Ouvrir un `.sttproj` existant.
- [ ] Lire la transcription.
- [ ] Modifier la transcription.
- [ ] Lire l'audio associé s'il existe.
- [ ] Sauvegarder le projet.
- [ ] Exporter TXT/JSON/DOCX/PDF.
- [ ] Créer un projet à partir d'un média.
- [ ] Prétraiter un audio/une vidéo.
- [ ] Écouter le résultat.
- [ ] Finaliser/exporter le fichier audio traité.

## P3.3 Fonctions nécessitant l'API

- [ ] Bloquer l'appel réel à ElevenLabs en l'absence de clé.
- [ ] `Nouvelle transcription > Direct` : informer avant d'ouvrir/lancer l'étape API.
- [ ] `Transcrire` après prétraitement : informer et proposer `Ouvrir les paramètres`.
- [ ] `Compte ElevenLabs` : désactiver ou afficher un message explicite sans clé.
- [ ] Ne jamais émettre une requête HTTP avec une clé vide.

## P3.4 UX recommandée

- [ ] Conserver si possible le bouton `Transcrire` visible.
- [ ] Au clic sans clé : message `Clé API requise` + `Ouvrir les paramètres` + `Annuler`.
- [ ] Afficher discrètement sur l'accueil `Service de transcription : non configuré`.

## Tests P3

- [ ] Démarrage sans clé.
- [ ] Ouverture d'un projet existant sans clé.
- [ ] Modification + sauvegarde sans clé.
- [ ] Export TXT/JSON/DOCX/PDF sans clé.
- [ ] Lecture audio sans clé.
- [ ] Tentative de transcription directe sans clé : aucune requête réseau.
- [ ] Tentative après prétraitement sans clé : aucune requête réseau.
- [ ] Ajout d'une clé depuis Paramètres puis transcription disponible sans redémarrage.
- [ ] Suppression de la clé puis transcription à nouveau bloquée.

**Critère de sortie :** absence de clé = dégradation fonctionnelle contrôlée, jamais blocage global de l'application.

---

# Phase 4 — Découplage finalisation audio / transcription

## Objectif

Supprimer le couplage actuel entre `process_and_transcribe()` et la finalisation du fichier audio.

## Fichiers concernés

- `ui/audio_preprocess_dialog.py`
- `services/audio_finalization_worker.py`
- `ui/home_window.py`

## P4.1 Séparer les opérations

- [ ] Isoler `finalize_audio()` de `transcribe_audio()`.
- [ ] La finalisation ne doit dépendre d'aucune clé API.
- [ ] Après traitement, permettre `Finaliser / Exporter l'audio`.
- [ ] Une fois finalisé, permettre éventuellement `Transcrire` si l'API est disponible.
- [ ] Déterminer explicitement ce que signifie `preprocessing_validated` lorsque l'utilisateur finalise sans transcrire.

## P4.2 Cycle de vie du projet provisoire

- [ ] Un projet contenant un audio finalisé sans transcription ne doit pas être supprimé par erreur.
- [ ] Définir l'état `provisoire`, `audio_finalisé`, `transcrit` ou une logique équivalente.
- [ ] La fermeture après export/finalisation doit conserver le projet conformément au choix utilisateur.
- [ ] L'abandon avant validation doit continuer à nettoyer les fichiers temporaires.

## Tests P4

- [ ] Prétraiter sans API.
- [ ] Finaliser en WAV.
- [ ] Finaliser MP3/M4A/FLAC/OGG/OPUS selon média d'entrée supporté.
- [ ] Vidéo → extraction/finalisation M4A sans API.
- [ ] Fermer après traitement non validé → nettoyage.
- [ ] Finaliser puis fermer → fichier final conservé.
- [ ] Finaliser puis renseigner une clé → transcription possible.
- [ ] Vérifier qu'aucun WAV temporaire n'est présenté comme fichier final.

**Critère de sortie :** le pipeline audio est un module autonome dont la transcription est une étape optionnelle postérieure.

---

# Phase 5 — Résilience face à un média manquant

## Objectif

Un média manquant ne doit jamais empêcher l'accès à une transcription existante.

## P5.1 Stratégie de récupération

- [ ] Résoudre d'abord le chemin relatif normal.
- [ ] Pour ancien projet, tenter l'ancien chemin absolu s'il existe.
- [ ] Tenter le même nom de fichier dans le dossier du projet.
- [ ] Si échec, afficher `Localiser le fichier... / Ouvrir sans audio / Annuler`.
- [ ] Si l'utilisateur relocalise le média, mettre à jour la référence en mémoire.
- [ ] À la sauvegarde, convertir la nouvelle référence en relatif si possible.

## P5.2 Mode transcription sans média

- [ ] Ouvrir l'éditeur même sans audio.
- [ ] Désactiver proprement lecture, seek et fonctions synchronisées nécessitant le média.
- [ ] Conserver édition, intervenants, timeline fondée sur horodatages si possible, sauvegarde et exports.
- [ ] Afficher un état `Audio indisponible` sans multiplier les erreurs FFmpeg/Qt.

## Tests P5

- [ ] Projet normal avec audio présent.
- [ ] Projet déplacé avec audio présent dans le même dossier.
- [ ] Projet dont seul l'audio a été déplacé.
- [ ] Relocalisation manuelle vers le bon audio.
- [ ] Ouverture sans audio.
- [ ] Sauvegarde et export sans audio.
- [ ] Réouverture après relocalisation.
- [ ] Vérifier absence du message Qt `Could not open media` dans le chemin nominal géré par l'application.

---

# Phase 6 — Couche de chemins et ressources multiplateforme

## Objectif

Éliminer les hypothèses Windows du code métier.

## P6.1 `app_paths.py`

- [ ] Réserver `platformdirs` aux données/cache/configuration applicatives.
- [ ] Utiliser `QStandardPaths` pour les dossiers utilisateur proposés dans l'UI.
- [ ] Renommer `PROJECTS_DIR` en notion de `DEFAULT_PROJECTS_DIR` si encore nécessaire.
- [ ] Ne plus créer automatiquement le répertoire de projets lors de l'import de `app_paths.py`.
- [ ] Centraliser les chemins applicatifs.

## P6.2 Audit `pathlib`

- [ ] Rechercher les concaténations manuelles de chemins.
- [ ] Rechercher les `"C:\\"` codés en dur.
- [ ] Rechercher les `split("\\")` / `replace("\\", "/")`.
- [ ] Utiliser `Path` pour les chemins locaux.
- [ ] Garantir que les noms générés restent compatibles Windows afin qu'un projet Linux/macOS puisse être copié vers Windows.

## P6.3 Temporaire et cache

- [ ] Renommer le dossier temporaire `TranscriptAudio` → `TranscriptStudio`.
- [ ] Éviter les collisions de fichiers temporaires entre deux médias de même nom.
- [ ] Prévoir à terme des sous-répertoires temporaires uniques par session/projet.
- [ ] Vérifier nettoyage au succès et à l'abandon sur les trois OS.

## Tests P6

- [ ] Chemins avec espaces.
- [ ] Chemins avec accents.
- [ ] Chemins Unicode.
- [ ] Projet sur volume/disque différent.
- [ ] Dossier projet en lecture seule.
- [ ] Deux fichiers source portant le même nom depuis deux répertoires différents.
- [ ] Aucun chemin Windows codé en dur dans les `.sttproj` neufs.

---

# Phase 7 — FFmpeg multiplateforme

## Objectif

Remplacer l'hypothèse actuelle `tools/ffmpeg/ffmpeg.exe`.

## P7.1 Résolveur FFmpeg

- [ ] Remplacer la constante Windows-only par un résolveur de dépendance.
- [ ] Définir les noms d'exécutables selon la plateforme (`ffmpeg.exe` / `ffmpeg`).
- [ ] Définir une stratégie prioritaire claire : binaire embarqué, configuration utilisateur, `PATH`, ou combinaison documentée.
- [ ] Centraliser toute détection dans `services/ffmpeg_paths.py` ou un nouveau `DependencyManager`.
- [ ] Conserver les services audio indépendants de la plateforme.
- [ ] Produire un message d'erreur adapté lorsque FFmpeg est absent ou non exécutable.

## P7.2 Organisation des binaires

Stratégie à figer avant packaging, par exemple :

```text
tools/ffmpeg/
├── windows/ffmpeg.exe
├── macos/ffmpeg
└── linux/ffmpeg
```

ou usage du `PATH` en développement et inclusion spécifique au build.

- [ ] Vérifier les implications de licence/distribution avant d'embarquer un binaire.
- [ ] Documenter l'installation de développement pour chaque OS.

## Tests P7

- [ ] FFmpeg trouvé dans l'emplacement embarqué attendu.
- [ ] FFmpeg trouvé via `PATH` si cette stratégie est retenue.
- [ ] FFmpeg absent → message explicite, pas de crash.
- [ ] FFmpeg non exécutable → erreur explicite.
- [ ] Trim seul.
- [ ] Suppression des silences seule.
- [ ] Accélération seule.
- [ ] Les trois traitements combinés.
- [ ] Finalisation de chaque format supporté.
- [ ] Extraction audio des formats vidéo supportés.

---

# Phase 8 — UI multiplateforme

## P8.1 Thèmes

- [ ] Supprimer `app.setStyle("Windows11")` comme dépendance globale.
- [ ] Choisir `Fusion` ou une stratégie native testée sur les trois plateformes.
- [ ] Vérifier System / Clair / Sombre sur chacun des OS.
- [ ] Vérifier lisibilité des contrôles désactivés.
- [ ] Vérifier QComboBox, boutons, timeline, waveform et dialogues.

## P8.2 Polices

- [ ] Supprimer la dépendance explicite à `Segoe UI Light`.
- [ ] Utiliser la police système et ajuster taille/poids.
- [ ] Tester le rendu des symboles/emoji actuellement utilisés comme boutons.
- [ ] Remplacer les emoji critiques par des SVG si leur rendu varie trop entre OS.

## P8.3 Icônes

- [ ] Utiliser PNG/SVG pour les icônes internes à l'UI.
- [ ] Prévoir `.ico` pour le package Windows.
- [ ] Prévoir `.icns` pour macOS.
- [ ] Prévoir PNG/SVG adapté pour Linux.
- [ ] Ne pas faire dépendre le démarrage Qt de `icons/icon.ico` uniquement.

## P8.4 Raccourcis

- [ ] Examiner `Ctrl+S` et utiliser un raccourci standard Qt (`QKeySequence.StandardKey.Save`) si approprié.
- [ ] Vérifier comportement attendu `Cmd+S` sous macOS.

## Tests P8

- [ ] Démarrage en thème système clair.
- [ ] Démarrage en thème système sombre.
- [ ] Forçage clair.
- [ ] Forçage sombre.
- [ ] Aucun texte illisible.
- [ ] Icônes visibles et homogènes.
- [ ] Raccourci sauvegarde natif sur chaque OS.
- [ ] Redimensionnement et plein écran/maximisation corrects.

---

# Phase 9 — Stockage sécurisé des clés API

## Objectif

Retirer progressivement la clé API de `settings.json` en clair, tout en restant multiplateforme.

## P9.1 Abstraction

- [ ] Créer `CredentialStore`.
- [ ] Exposer `get_api_key()`, `set_api_key()`, `delete_api_key()`, `has_api_key()`.
- [ ] Faire dépendre ElevenLabs de cette abstraction plutôt que directement de la structure JSON.
- [ ] Prévoir plusieurs fournisseurs futurs sans imposer une unique clé globale.

## P9.2 Migration

- [ ] Détecter une ancienne clé présente dans `settings.json`.
- [ ] La migrer vers le stockage sécurisé retenu.
- [ ] Confirmer la réussite avant de retirer la valeur en clair.
- [ ] Ne jamais journaliser la clé.
- [ ] Ne jamais inclure la clé dans un dump projet ou un export.

## Tests P9

- [ ] Première saisie clé.
- [ ] Lecture après redémarrage.
- [ ] Modification clé.
- [ ] Suppression clé.
- [ ] Migration d'une ancienne configuration.
- [ ] Échec du stockage sécurisé sans perte silencieuse de la clé existante.
- [ ] Vérifier que `settings.json` ne contient plus le secret après migration réussie.

---

# Phase 10 — Nettoyage du nom historique et dette ciblée

## P10.1 `TranscriptAudio` → `TranscriptStudio`

- [ ] Rechercher toutes les occurrences texte `TranscriptAudio`.
- [ ] Corriger le dossier temporaire.
- [ ] Corriger documentation et commentaires pertinents.
- [ ] Ne pas modifier aveuglément les références historiques nécessaires à une migration.

## P10.2 Nettoyages détectés dans le dump

- [ ] Supprimer la première définition dupliquée de `_update_media_mode()` dans `TranscriptionEntryDialog` après vérification de la version à conserver.
- [ ] Nettoyer les imports dupliqués constatés dans certains fichiers.
- [ ] Vérifier la cohérence des noms `project.json` historiques dans la documentation avec le format réel `project.sttproj`.
- [ ] Mettre le README en cohérence avec le nouveau first-run et le mode sans API.

## Tests P10

- [ ] Recherche globale ne trouve plus d'occurrence historique non justifiée.
- [ ] Démarrage normal.
- [ ] Sélection audio et vidéo normal.
- [ ] Détection vidéo toujours fonctionnelle après suppression de la méthode dupliquée.

---

# Phase 11 — Suite de tests automatisés et CI multiplateforme

## Objectif

Passer de l'actuel `test/test.py` essentiellement manuel à une suite de non-régression.

## P11.1 Structure proposée

```text
tests/
├── unit/
│   ├── test_project_io.py
│   ├── test_settings.py
│   ├── test_project_manager.py
│   ├── test_media_formats.py
│   ├── test_silence_detection.py
│   └── test_ffmpeg_resolver.py
├── integration/
│   ├── test_project_portability.py
│   ├── test_audio_pipeline.py
│   └── test_legacy_project_migration.py
└── fixtures/
    ├── projects/
    └── media/
```

- [ ] Conserver des médias de test courts et légalement redistribuables/générés pour les tests.
- [ ] Ne jamais inclure une vraie clé API.
- [ ] Mock/fake des appels ElevenLabs dans la suite automatique normale.
- [ ] Tests réseau réels optionnels et explicitement séparés.

## P11.2 Matrice CI

- [ ] Windows + Python supporté.
- [ ] Ubuntu/Linux + Python supporté.
- [ ] macOS + Python supporté.
- [ ] `python -m pip check`.
- [ ] `pytest`.
- [ ] Validation minimale de lancement/import Qt compatible avec l'environnement CI.

**Critère de sortie :** une modification qui casse chemins/projets/tests de base sur un OS est détectée avant merge.

---

# Phase 12 — Packaging multiplateforme

> À lancer seulement après validation du code source sur les trois OS.

## Windows

- [ ] Build Nuitka reproductible.
- [ ] Inclusion des ressources.
- [ ] Inclusion/résolution FFmpeg conforme à la stratégie retenue.
- [ ] Icône application `.ico`.
- [ ] Installateur à définir/tester.
- [ ] Test sur machine Windows sans environnement Python de dev.

## macOS

- [ ] Build natif sur macOS.
- [ ] Bundle `.app`.
- [ ] Icône `.icns`.
- [ ] FFmpeg disponible dans le bundle ou détecté selon stratégie.
- [ ] Vérifier permissions/quarantaine/signature selon mode de distribution retenu.
- [ ] Tester `Cmd+S`, dialogues natifs et lecture multimédia.

## Linux

- [ ] Build natif Linux.
- [ ] Format de distribution à sélectionner après essais (AppImage/Flatpak/autre).
- [ ] Vérifier dépendances Qt Multimedia et audio.
- [ ] FFmpeg disponible selon stratégie.
- [ ] Tester au minimum une distribution cible définie.

---

# Programme de test complet de la campagne

## A. Préparation de l'environnement de recette

Pour chaque OS validé :

- [ ] Installation propre des dépendances.
- [ ] `python -m pip check` sans erreur.
- [ ] FFmpeg validé.
- [ ] Préparer une configuration sans clé API.
- [ ] Préparer une configuration avec clé API de test, uniquement pour la recette réseau contrôlée.
- [ ] Sauvegarder un exemplaire de plusieurs anciens `.sttproj` avant migration.

### Jeu de médias minimal

- [ ] WAV court.
- [ ] MP3 court.
- [ ] M4A/AAC.
- [ ] FLAC.
- [ ] OGG.
- [ ] OPUS.
- [ ] MP4 contenant de l'audio.
- [ ] Un autre format vidéo réellement supporté par la chaîne FFmpeg.
- [ ] Audio avec silence connu.
- [ ] Audio dont le nom contient espaces et accents.

## B. Tests premier lancement

- [ ] B01 Installation/configuration vierge → Paramètres obligatoires.
- [ ] B02 Chemin Documents proposé correctement.
- [ ] B03 Validation chemin proposé sans clé → succès.
- [ ] B04 Choix chemin personnalisé → succès.
- [ ] B05 Chemin vide → refus.
- [ ] B06 Chemin non accessible → refus contrôlé.
- [ ] B07 Fermeture X avant validation → application quitte sans valider.
- [ ] B08 Relance après validation → accueil direct.
- [ ] B09 Clé facultative → pas d'erreur au démarrage.
- [ ] B10 Configuration existante valide → pas de reset ni déplacement automatique.

## C. Tests gestion projets et portabilité

- [ ] C01 Création projet direct.
- [ ] C02 Création projet avec prétraitement.
- [ ] C03 Création dans `Commun`.
- [ ] C04 Création dans catégorie personnalisée.
- [ ] C05 Deux projets de même nom → suffixe correct.
- [ ] C06 `.sttproj` neuf contient un chemin média relatif.
- [ ] C07 `.sttproj` neuf ne persiste pas `project_file`.
- [ ] C08 Déplacer le dossier projet dans le même volume → ouverture OK.
- [ ] C09 Déplacer vers un autre volume → ouverture OK.
- [ ] C10 Copier vers un autre répertoire → les deux copies restent indépendantes.
- [ ] C11 Sauvegarder la copie → original inchangé.
- [ ] C12 Ouvrir ancien `.sttproj` avec ancien chemin toujours valide.
- [ ] C13 Ouvrir ancien `.sttproj` dont le dossier a été déplacé avec son audio.
- [ ] C14 Sauvegarder ancien projet → migration vers format portable.
- [ ] C15 Ouvrir projet avec média absent → dialogue de récupération.
- [ ] C16 Relocaliser média → lecture OK.
- [ ] C17 Ouvrir sans audio → transcript éditable/exportable.
- [ ] C18 Liste des récents : projet existant visible.
- [ ] C19 Projet récent supprimé/déplacé → nettoyage/gestion cohérente.

## D. Tests sans API

- [ ] D01 Accueil disponible.
- [ ] D02 Ouvrir projet existant.
- [ ] D03 Éditer mot.
- [ ] D04 Split/fusion blocs.
- [ ] D05 Renommer/créer intervenant.
- [ ] D06 Sauvegarder.
- [ ] D07 Autosave.
- [ ] D08 Export TXT.
- [ ] D09 Export JSON.
- [ ] D10 Export DOCX.
- [ ] D11 Export PDF.
- [ ] D12 Prétraiter audio.
- [ ] D13 Prétraiter vidéo.
- [ ] D14 Finaliser/exporter audio.
- [ ] D15 Tentative transcription directe → message API requise, aucune requête.
- [ ] D16 Tentative transcription après prétraitement → même comportement.
- [ ] D17 Compte ElevenLabs sans clé → comportement explicite.

## E. Tests avec API ElevenLabs

> Ces tests engagent le service externe et doivent être exécutés sur un média court contrôlé.

- [ ] E01 Tester connexion avec clé valide.
- [ ] E02 Clé invalide → message propre.
- [ ] E03 Transcription directe audio.
- [ ] E04 Transcription après prétraitement.
- [ ] E05 Diarisation ON.
- [ ] E06 Diarisation OFF.
- [ ] E07 Auto-détection langue.
- [ ] E08 Langue imposée.
- [ ] E09 Enregistrement `transcription.json`.
- [ ] E10 Création `project.sttproj` portable après réponse API.
- [ ] E11 Réouverture et synchronisation audio/transcript.

## F. Tests audio

- [ ] F01 Chargement waveform.
- [ ] F02 Lecture/pause/stop original.
- [ ] F03 Seek original.
- [ ] F04 Zoom/pan waveform.
- [ ] F05 Trim début/fin.
- [ ] F06 Suppression silences buffer 0.
- [ ] F07 Suppression silences buffer 0,2 s.
- [ ] F08 Accélération.
- [ ] F09 Trim + silences.
- [ ] F10 Trim + vitesse.
- [ ] F11 Silences + vitesse.
- [ ] F12 Les trois traitements.
- [ ] F13 Comparer durée estimée/réelle selon tolérance définie.
- [ ] F14 Retraitement successif remet correctement le résultat à zéro.
- [ ] F15 Abandon traitement → nettoyage.
- [ ] F16 Finalisation → temporaires supprimés, final conservé.
- [ ] F17 Nom de fichier avec accents/espaces.

## G. Tests éditeur et non-régression

- [ ] G01 Lecture synchronisée.
- [ ] G02 Mot actif.
- [ ] G03 Timeline seek.
- [ ] G04 Zoom timeline boutons.
- [ ] G05 Zoom timeline molette centré correctement.
- [ ] G06 Pan timeline.
- [ ] G07 Changement intervenant depuis bloc.
- [ ] G08 Changement intervenant depuis timeline.
- [ ] G09 Renommage intervenant.
- [ ] G10 Création intervenant.
- [ ] G11 Nettoyage intervenants inutilisés.
- [ ] G12 Split avant.
- [ ] G13 Split après.
- [ ] G14 Fusion blocs.
- [ ] G15 Taille texte +/-.
- [ ] G16 Sauvegarde raccourci natif.
- [ ] G17 Fermeture projet modifié : Save/Discard/Cancel.
- [ ] G18 Retour accueil avec projet modifié.

## H. Tests thèmes/UI par OS

Exécuter Windows/macOS/Linux :

- [ ] H01 Thème système clair.
- [ ] H02 Thème système sombre.
- [ ] H03 Thème clair forcé.
- [ ] H04 Thème sombre forcé.
- [ ] H05 Contrôles désactivés lisibles.
- [ ] H06 Dialogues fichiers fonctionnels.
- [ ] H07 Icônes visibles.
- [ ] H08 Aucun bouton critique dépend d'un emoji manquant.
- [ ] H09 Maximisation Home/Prétraitement/Éditeur correcte.
- [ ] H10 Mise à l'échelle HiDPI acceptable.

## I. Tests croisés entre plateformes

À effectuer dès que les trois environnements sont disponibles :

- [ ] I01 Créer/sauvegarder sous Windows → ouvrir sous macOS.
- [ ] I02 Windows → Linux.
- [ ] I03 macOS → Windows.
- [ ] I04 macOS → Linux.
- [ ] I05 Linux → Windows.
- [ ] I06 Linux → macOS.
- [ ] I07 Après transfert, lecture média.
- [ ] I08 Après transfert, édition + sauvegarde.
- [ ] I09 Après retour sur OS d'origine, réouverture du projet modifié.
- [ ] I10 Vérifier absence de `C:\\...`, `/Users/...` ou `/home/...` dans les références portables nouvellement sauvegardées.

## J. Tests packaging

Pour chaque OS distribué :

- [ ] J01 Installation sur machine propre/VM.
- [ ] J02 Premier lancement.
- [ ] J03 Accès Documents natif.
- [ ] J04 Création dossier projets.
- [ ] J05 FFmpeg détecté.
- [ ] J06 Prétraitement audio.
- [ ] J07 Lecture Qt Multimedia.
- [ ] J08 Ouverture `.sttproj`.
- [ ] J09 Export TXT/JSON/DOCX/PDF.
- [ ] J10 Désinstallation/mise à jour sans suppression des projets utilisateur.

---

# Ordre de commits recommandé

- [ ] **Commit 25 — Portable project format** : chemins relatifs, `project_file` non persisté, migration anciens projets.
- [ ] **Commit 26 — First-run setup** : répertoire projets obligatoire, Documents proposé, clé facultative.
- [ ] **Commit 27 — API capability mode** : utilisation sans clé, blocage ciblé des fonctions ElevenLabs.
- [ ] **Commit 28 — Audio finalization decoupling** : finaliser/exporter sans transcrire.
- [ ] **Commit 29 — Missing media recovery** : relocalisation et ouverture sans audio.
- [ ] **Commit 30 — Cross-platform paths** : chemins système, temporaires et conventions portables.
- [ ] **Commit 31 — Cross-platform FFmpeg** : résolveur et stratégie des binaires.
- [ ] **Commit 32 — Cross-platform UI** : style, police, icônes, raccourcis.
- [ ] **Commit 33 — Secure credentials** : abstraction et migration de la clé.
- [ ] **Commit 34 — Cleanup / historical naming** : `TranscriptAudio`, méthode dupliquée et documentation.
- [ ] **Commit 35 — Automated tests / CI** : suite pytest et matrice OS.
- [ ] **Commit 36+ — Packaging** : builds natifs Windows, macOS, Linux.

---

# Garde-fous avant chaque commit

- [ ] `git status` propre ou changements parfaitement identifiés.
- [ ] Tests automatisés concernés verts.
- [ ] Tests manuels ciblés du commit effectués.
- [ ] Aucune vraie clé API dans les fichiers suivis par Git.
- [ ] Aucun média utilisateur ajouté accidentellement au dépôt.
- [ ] Aucun `.sttproj` de fixture ne contient de donnée personnelle/confidentielle.
- [ ] README/architecture mis à jour lorsque le contrat fonctionnel change.

# Definition of Done globale

La campagne est terminée lorsque :

- [ ] Un projet neuf est portable par conception.
- [ ] Les anciens projets restent ouvrables et migrent sans perte.
- [ ] Un projet peut être déplacé/copier puis sauvegardé sans référence à son ancien emplacement.
- [ ] Le premier lancement impose un répertoire projets valide.
- [ ] La clé API demeure facultative.
- [ ] Sans clé, prétraitement, finalisation, ouverture, édition et exports restent utilisables.
- [ ] Un média absent n'empêche pas l'ouverture du transcript.
- [ ] Le code source fonctionne sur Windows, macOS et Linux pour le périmètre validé.
- [ ] FFmpeg est résolu proprement sur chaque plateforme cible.
- [ ] L'UI n'est plus dépendante du style/police/icône Windows.
- [ ] La clé API n'est plus conservée en clair après mise en place du stockage sécurisé.
- [ ] La suite `pytest` couvre les règles de portabilité critiques.
- [ ] Les tests croisés Windows/macOS/Linux sont validés.
- [ ] Chaque package distribué est testé sur une installation propre.

---

# Notes de planification

1. **Ne pas fusionner portabilité des `.sttproj` et first-run dans le même commit.** Le premier corrige un contrat de fichier, le second un comportement de configuration.
2. **Ne pas implémenter le stockage sécurisé de la clé avant d'avoir stabilisé le first-run.** Cela permet de diagnostiquer chaque évolution séparément.
3. **Tester le code source sur macOS/Linux avant de travailler le packaging.** Un build ne doit pas servir à découvrir les dépendances implicites de la plateforme.
4. **Pour les projets portables, le dossier contenant `project.sttproj` est l'ancre de résolution.** Le `projects_root` ne sert qu'à la création/navigation par défaut.
5. **Les chemins absolus dans `recent_projects` restent acceptables comme préférence locale utilisateur.** Ils ne font pas partie du format portable du projet et doivent simplement être nettoyés quand ils deviennent invalides.
