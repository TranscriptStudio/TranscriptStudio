# Transcript Studio V1.1 - Checklist

## Phase 0 - Préparation
- [x] Tag Git v1.0.0
- [x] Branche edition_audio
- [ ] Vérifier build Nuitka
- [ ] Vérifier build MSI

## Phase 1 - Nouveau workflow
### TranscriptionEntryDialog
- [x] Création du dialogue
- [x] Sélection du fichier audio
- [x] Choix Prétraitement / Direct
- [x] Retour du mode choisi

### HomeWindow
- [x] Ouverture de TranscriptionEntryDialog
- [ ] Brancher mode direct
- [ ] Brancher mode prétraitement

### NewTranscriptionDialog
- [x] Suppression du choix du fichier
- [x] Passage du fichier au constructeur
- [ ] Validation complète du workflow

## Phase 2 - AudioPreprocessDialog
- [ ] Créer audio_preprocess_dialog.py
- [ ] Afficher le fichier chargé
- [ ] Créer la barre d'outils
- [ ] Implémenter les actions associées

## Phase 3 - Lecture audio
- [ ] Réutiliser PlaybackManager
- [ ] Lecture
- [ ] Pause
- [ ] Stop
- [ ] Affichage temps courant

## Phase 4 - WaveformWidget
### Préparation
- [ ] Installer pyqtgraph
- [ ] Vérifier compatibilité PySide6

### Affichage
- [ ] Afficher la forme d'onde
- [ ] Zoom avant
- [ ] Zoom arrière
- [ ] Fit
- [ ] Déplacement horizontal

### Curseurs
- [ ] Curseur lecture
- [ ] Curseur découpe
- [ ] Bulle temporelle
- [ ] Drag & drop

### Auto-scroll
- [ ] Déplacement du curseur en lecture
- [ ] Scroll uniquement hors écran
- [ ] Pas de pompage d'affichage

## Phase 5 - Paramètres traitement
### Modèle
- [ ] Créer AudioProcessingSettings

### Effets
- [ ] Couper avant le curseur
- [ ] Supprimer les silences
- [ ] Paramètres avancés TranscriptAudio
- [ ] Accélération 0 → 100%
- [ ] Couleurs vert/orange/rouge

## Phase 6 - FFmpeg
- [ ] Détecter ffmpeg
- [ ] Détecter ffprobe
- [ ] Coupe du début
- [ ] Suppression des silences
- [ ] Accélération
- [ ] Pipeline unique FFmpeg

## Phase 7 - Gestion des fichiers
- [ ] Générer audio_processed.ext
- [ ] Préserver audio_original.ext
- [ ] Retour original
- [ ] Sauvegarde projet

## Phase 8 - Intégration ElevenLabs
- [ ] Bouton Transcrire
- [ ] Passage de l'audio traité
- [ ] Ouverture NewTranscriptionDialog

## Phase 9 - Validation
### Formats
- [ ] MP3
- [ ] WAV
- [ ] M4A
- [ ] AAC
- [ ] FLAC
- [ ] OGG
- [ ] OPUS
- [ ] MP4
- [ ] MOV
- [ ] MKV
- [ ] AVI
- [ ] WEBM

### Fonctionnel
- [ ] Lecture
- [ ] Coupe
- [ ] Suppression silences
- [ ] Accélération
- [ ] Sauvegarde
- [ ] Réouverture projet
- [ ] Transcription

### Packaging
- [ ] Build Nuitka
- [ ] Build WiX MSI
- [ ] Test installation

## Fin V1.1
- [ ] Workflow complet sans Audacity
- [ ] Ecoute du fichier traité
- [ ] Paramètres sauvegardés
- [ ] Build final validé
