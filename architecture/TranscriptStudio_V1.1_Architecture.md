# Transcript Studio V1.1 - Architecture

## Workflow cible

Accueil
→ Nouvelle transcription
→ TranscriptionEntryDialog
→ Choix du fichier audio
→ Choix du mode
  - Prétraitement audio
  - Transcription directe

### Parcours direct

TranscriptionEntryDialog
→ NewTranscriptionDialog
→ Transcription ElevenLabs

### Parcours prétraitement

TranscriptionEntryDialog
→ AudioPreprocessDialog
→ Traitement audio
→ Ecoute de validation
→ NewTranscriptionDialog
→ Transcription ElevenLabs

---

## Nouveaux fichiers

### UI

ui/
- transcription_entry_dialog.py
- audio_preprocess_dialog.py
- waveform_widget.py

### Services

services/
- audio_preprocessor.py
- audio_waveform_service.py

### Models

models/
- audio_processing_settings.py

---

## Structure projet

Projet/
│
├── audio_original.ext
├── audio_processed.ext
├── project.json
└── exports/

L'audio original n'est jamais modifié.

---

## AudioPreprocessDialog

### Barre d'outils

- ↶ Retour original
- ▶ Lecture
- ⏸ Pause
- ⏹ Stop
- ✨ Effets
- 🔄 Traiter
- 💾 Sauvegarder
- ☁ Transcrire

### Forme d'onde

Fonctions :
- zoom horizontal
- déplacement horizontal
- curseur de lecture
- curseur de découpe
- bulle temporelle
- déplacement des curseurs par glisser-déposer
- auto-scroll uniquement lorsque le curseur quitte la zone visible

### Effets

#### Couper avant le curseur

Suppression de tout ce qui précède le curseur orange.

#### Suppression des silences

Paramètres avancés :
- seuil
- durée minimale
- conserver avant/après

Valeurs par défaut reprises de TranscriptAudio.

#### Accélération

Curseur 0 → 100 %

- 0 % = x1.00
- 50 % = x1.50
- 100 % = x2.00

Couleur :
- vert
- orange
- rouge

---

## Traitement FFmpeg

Le traitement réel est réalisé uniquement au clic sur :

🔄 Traiter

Le fichier audio traité est généré dans :

audio_processed.ext

Aucune estimation théorique n'est réalisée.

Le gain affiché est calculé sur le résultat réel obtenu.

---

## Affichages

- Durée originale
- Durée traitée
- Réduction obtenue (%)

---

## Technologies

- PlaybackManager
- QMediaPlayer
- FFmpeg
- pyqtgraph

---

## Objectif V1.1

Remplacer le workflow Audacity :

1. Couper le début
2. Supprimer les silences
3. Accélérer
4. Réécouter
5. Transcrire

sans quitter Transcript Studio.
