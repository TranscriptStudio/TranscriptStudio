# Transcript Studio V1.1 - Checklist de Développement

## Phase 0 - Sécurisation

- [x ] Commit Git V1.0 stable
- [x ] Créer le tag Git `v1.0.0`
- [x ] Créer la branche `edition_audio`
- [ ] Vérifier que le build Nuitka est reproductible
- [ ] Vérifier que le MSI V1.0 est toujours générable

---

## Phase 1 - Nouveau workflow

### 1.1 Créer TranscriptionEntryDialog

- [x ] Créer `ui/transcription_entry_dialog.py`
- [x ] Ajouter un champ fichier audio
- [x ] Ajouter le bouton Parcourir
- [x ] Ajouter le bouton « Préparer l'audio »
- [x ] Ajouter le bouton « Transcrire directement »
- [x ] Retourner le chemin du fichier sélectionné

### 1.2 Modifier HomeWindow

- [x ] Remplacer l'ouverture directe de NewTranscriptionDialog
- [x ] Ouvrir TranscriptionEntryDialog
- [x ] Tester les deux parcours

### 1.3 Adapter NewTranscriptionDialog

- [x ] Supprimer la sélection du fichier audio
- [x ] Passer le fichier en paramètre du constructeur
- [x ] Conserver les paramètres ElevenLabs existants
- [x ] Vérifier diarisation ON/OFF

---

## Phase 2 - Fenêtre Prétraitement Audio

### 2.1 Créer AudioPreprocessDialog

- [x ] Créer `ui/audio_preprocess_dialog.py`
- [x ] Afficher le nom du fichier
- [x ] Préparer la structure générale

### 2.2 Barre d'outils

- [x ] Bouton Retour original
- [x ] Bouton Lecture
- [x ] Bouton Pause
- [x ] Bouton Stop
- [x ] Bouton Effets
- [x ] Bouton Traiter
- [x ] Bouton Sauvegarder
- [x ] Bouton Transcrire

### 2.3 Intégration PlaybackManager

- [x ] Charger automatiquement le fichier
- [x ] Lecture fonctionnelle
- [x ] Pause fonctionnelle
- [x ] Stop fonctionnel
- [x ] Affichage du temps courant

---

## Phase 3 - Forme d'onde

### 3.1 Préparation

- [x ] Installer pyqtgraph
- [x ] Vérifier compatibilité avec PySide6
- [x ] Choisir la stratégie FFmpeg
- [x ] Embarquer ffmpeg.exe
- [x ] Embarquer ffprobe.exe
- [x ] Ajouter le service de découverte de chemins

### 3.2 Créer WaveformWidget

- [x ] Créer `ui/waveform_widget.py`
- [x ] Charger les données audio
- [x ] Afficher la forme d'onde

### 3.3 Navigation

- [ ] Zoom avant
- [ ] Zoom arrière
- [ ] Fit complet
- [ ] Déplacement horizontal

### 3.4 Curseurs

- [ ] Curseur lecture rouge
- [ ] Curseur découpe orange
- [ ] Déplacement du curseur découpe

---

## Phase 4 - Paramètres de traitement

### 4.1 Modèle

- [ ] Créer `models/audio_processing_settings.py`
- [ ] Définir tous les paramètres

### 4.2 Panneau Effets

- [ ] Affichage/Masquage via le bouton Effets

### 4.3 Coupe du début

- [ ] Ajouter la case Activer
- [ ] Utiliser le curseur orange comme point de coupe

### 4.4 Suppression des silences

- [ ] Ajouter la case Activer
- [ ] Ajouter seuil dB
- [ ] Ajouter durée minimale
- [ ] Ajouter conserver avant/après
- [ ] Charger les valeurs par défaut TranscriptAudio

### 4.5 Accélération

- [ ] Ajouter la case Activer
- [ ] Ajouter curseur 0 → 100 %
- [ ] Afficher le pourcentage
- [ ] Afficher le facteur x1.00 → x2.00
- [ ] Couleur verte/orange/rouge

---

## Phase 5 - Estimation

### 5.1 AudioPreprocessor

- [ ] Créer `services/audio_preprocessor.py`
- [ ] Calcul de durée estimée
- [ ] Calcul du gain estimé

### 5.2 Interface

- [ ] Afficher durée originale
- [ ] Afficher durée estimée
- [ ] Afficher réduction estimée

---

## Phase 6 - FFmpeg

### 6.1 Vérification

- [ ] Détecter ffmpeg
- [ ] Détecter ffprobe

### 6.2 Coupe du début

- [ ] Générer l'audio traité
- [ ] Vérifier la durée obtenue

### 6.3 Suppression des silences

- [ ] Appliquer les paramètres
- [ ] Vérifier le résultat

### 6.4 Accélération

- [ ] Appliquer le facteur choisi
- [ ] Vérifier la durée finale

### 6.5 Chaînage

- [ ] Exécuter tous les traitements dans un seul pipeline FFmpeg

---

## Phase 7 - Sauvegarde projet

### 7.1 Fichiers

- [ ] Conserver audio_original.ext
- [ ] Générer audio_processed.ext

### 7.2 Paramètres

- [ ] Sauvegarder audio_processing dans project.json

### 7.3 Réouverture

- [ ] Restaurer tous les paramètres
- [ ] Restaurer la position de coupe

---

## Phase 8 - Boutons finaux

### Retour original

- [ ] Supprimer audio_processed.ext
- [ ] Recharger audio_original.ext

### Sauvegarder

- [ ] Sauvegarder paramètres dans project.json

### Transcrire

- [ ] Ouvrir NewTranscriptionDialog
- [ ] Pré-remplir le bon fichier audio

---

## Phase 9 - Validation

### Formats

- [ ] MP3
- [ ] WAV
- [ ] M4A
- [ ] FLAC
- [ ] MP4

### Fonctionnel

- [ ] Lecture audio
- [ ] Coupe du début
- [ ] Suppression des silences
- [ ] Accélération
- [ ] Sauvegarde
- [ ] Réouverture projet
- [ ] Transcription ElevenLabs

### Packaging

- [ ] Build Nuitka
- [ ] Build MSI WiX
- [ ] Test installation MSI

---

## Critère de fin V1.1

- [ ] Prétraitement intégré entièrement dans Transcript Studio
- [ ] Aucun passage par Audacity nécessaire
- [ ] Audio traité réécoutable avant transcription
- [ ] Paramètres sauvegardés dans le projet
- [ ] Build Windows fonctionnel
