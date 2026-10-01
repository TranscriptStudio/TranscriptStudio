## Installation de FFmpeg

Transcript Studio nécessite FFmpeg pour le prétraitement et la
conversion des fichiers audio et vidéo.

Les exécutables FFmpeg ne sont pas inclus dans le dépôt Git.

### Téléchargement sous Windows

Télécharger la version **release essentials** de FFmpeg depuis :

https://www.gyan.dev/ffmpeg/builds/

Dans la section **release builds**, télécharger :

`ffmpeg-release-essentials.zip`

Après extraction de l'archive, récupérer le fichier :

`ffmpeg.exe`

puis le copier dans le répertoire suivant de Transcript Studio :

tools/ffmpeg/

La structure attendue est donc :

TranscriptStudio/
├── tools/
│   └── ffmpeg/
│       └── ffmpeg.exe
│       
├── services/
├── ui/
└── TranscriptStudio.py

Pour vérifier l'installation depuis PowerShell :

.\tools\ffmpeg\ffmpeg.exe -version
