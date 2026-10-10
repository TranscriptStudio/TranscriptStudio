# Transcript Studio

Transcript Studio est une application de bureau Windows dédiée au prétraitement audio, à la transcription via l’API ElevenLabs Speech-to-Text et à la relecture/correction des transcriptions obtenues.

Le projet est diffusé sous forme de **code source**. Aucun exécutable Windows n’est fourni dans le dépôt, mais les scripts de build de la version 1.0 (installateur et archive portable) sont inclus (voir la section « Build Windows »).

## Fonctionnalités principales

### Prétraitement audio

Transcript Studio permet de préparer un enregistrement avant transcription :

- découpe du début et de la fin ;
- détection et suppression des silences ;
- conservation d’un buffer autour des silences supprimés ;
- accélération de l’audio ;
- visualisation de la forme d’onde ;
- comparaison et écoute du résultat avant transcription.

Le fichier original est conservé. Le traitement génère un fichier audio distinct destiné à la transcription.

### Transcription ElevenLabs

Transcript Studio utilise directement l’API ElevenLabs Speech-to-Text. Une clé API ElevenLabs personnelle est nécessaire pour effectuer une nouvelle transcription.

L’interface permet notamment de définir :

- la langue ou l’auto-détection ;
- le modèle de transcription ;
- la diarisation ;
- la reconnaissance des intervenants connus ;
- la détection des rôles ;
- des mots-clés personnalisés.

### Éditeur de transcription

Après transcription, l’éditeur permet notamment de :

- relire la transcription de façon synchronisée avec l’audio ;
- visualiser le mot correspondant à la position de lecture ;
- modifier ou supprimer un mot ;
- séparer des blocs de parole ;
- fusionner des blocs appartenant au même intervenant ;
- réaffecter un bloc à un autre intervenant ;
- créer et renommer des intervenants ;
- supprimer les intervenants inutilisés ;
- modifier la taille du texte ;
- naviguer dans la transcription à l’aide d’une timeline ;
- sauvegarder le projet ;
- exporter la transcription.

### Timeline

La timeline représente chronologiquement les blocs de parole. Chaque intervenant possède une couleur et une ligne dédiées, ce qui permet d’identifier rapidement qui intervient et à quel moment dans l’enregistrement.

### Export

Les formats d’export actuellement proposés sont :

- TXT ;
- JSON ;
- DOCX ;
- PDF.

Selon le format, les intervenants et les horodatages peuvent être inclus.

## Formats multimédias pris en charge

### Audio

- WAV
- MP3
- M4A
- AAC
- FLAC
- OGG
- OPUS

### Vidéo

- MP4
- MOV
- MKV
- AVI
- WEBM
- MPEG
- MPG
- TS
- M2TS

Les fichiers vidéo passent obligatoirement par le prétraitement afin d’en extraire une piste audio avant transcription.

## Prérequis

Transcript Studio a été validé dans l’environnement suivant :

- Windows ;
- Python 3.11.15 ;
- dépendances Python listées dans `requirements.txt` ;
- FFmpeg installé dans l’arborescence du projet ;
- connexion Internet et clé API ElevenLabs pour les fonctions de transcription.

Le fonctionnement de cette version précise du projet a été validé avec Python 3.11.15. Cela ne signifie pas que les autres versions de Python sont nécessairement incompatibles, mais elles n’ont pas été validées dans le cadre de la préparation actuelle du dépôt.

## Installation depuis les sources

### 1. Cloner le dépôt

```powershell
git clone https://github.com/davidfrechet/TranscriptStudio.git
cd TranscriptStudio
```

Si le dépôt est encore privé, le compte GitHub utilisé doit disposer des droits d’accès nécessaires.

### 2. Créer un environnement Python isolé

Avec Conda :

```powershell
conda create -n transcript-studio python=3.11.15 pip -c conda-forge --override-channels
conda activate transcript-studio
```

Une autre méthode de création d’environnement virtuel peut être utilisée à condition de disposer d’un environnement Python compatible.

### 3. Installer les dépendances

```powershell
python -m pip install -r requirements.txt
```

Vérification recommandée :

```powershell
python -m pip check
```

Les dépendances Python directes actuellement déclarées sont :

- PySide6 6.11.2 ;
- NumPy 2.4.6 ;
- Requests 2.34.2 ;
- python-docx 1.2.0 ;
- ReportLab 5.0.1 ;
- platformdirs 4.11.5 ;
- pyqtgraph 0.14.0.

Les outils nécessaires uniquement au développement sont séparés dans `requirements-dev.txt`.

Pour les installer :

```powershell
python -m pip install -r requirements-dev.txt
```

## Installation de FFmpeg

FFmpeg est nécessaire au prétraitement et à la conversion des fichiers audio/vidéo.

**L'exécutable FFmpeg n'est pas fournis dans ce dépôt.**

Sous Windows, télécharger le package **release essentials** depuis :

https://www.gyan.dev/ffmpeg/builds/

Dans la section `release builds`, télécharger :

```text
ffmpeg-release-essentials.zip
```

À la date de préparation de ce README, la page Gyan propose FFmpeg 9.0.2 comme dernière release et fournit également une somme SHA-256 pour l’archive. Il est recommandé de vérifier les informations affichées sur la page de téléchargement avant installation.

Après extraction de l’archive, récupérer :

```text
ffmpeg.exe
```

et le copier dans :

```text
tools/ffmpeg/
```

La structure attendue est :

```text
TranscriptStudio/
├── tools/
│   └── ffmpeg/
│       └── ffmpeg.exe
│
├── models/
├── services/
├── ui/
├── requirements.txt
└── TranscriptStudio.py
```

Vérifier ensuite depuis PowerShell :

```powershell
.\tools\ffmpeg\ffmpeg.exe -version
```

Le code de Transcript Studio recherche explicitement cet exécutable à cet emplacement.

## Configuration ElevenLabs

Transcript Studio utilise l’API ElevenLabs Speech-to-Text pour produire les transcriptions.

Une clé API ElevenLabs est donc nécessaire pour lancer une nouvelle transcription.

Après démarrage de l’application :

```text
Accueil
→ Paramètres
→ Clé API ElevenLabs
```

Renseigner la clé puis utiliser `Tester la connexion`.

La clé API est enregistrée dans les données utilisateur locales de Transcript Studio et ne doit jamais être ajoutée au dépôt Git.

L’utilisation de l’API ElevenLabs est soumise aux conditions, limites et éventuels coûts du service ElevenLabs. Transcript Studio est un projet indépendant et n’est ni affilié à, ni sponsorisé, ni approuvé par ElevenLabs.

Documentation officielle Speech-to-Text :

https://elevenlabs.io/docs/overview/capabilities/speech-to-text

## Lancement

Depuis la racine du projet et après activation de l’environnement :

```powershell
python TranscriptStudio.py
```

Au premier lancement, Transcript Studio crée son répertoire de données utilisateur et un répertoire de projets par défaut.

## Organisation des projets

Le répertoire racine des projets peut être modifié depuis les paramètres.

Les projets peuvent être classés dans différents sous-répertoires. Le sous-répertoire `Commun` est créé et utilisé comme classement par défaut.

Exemple :

```text
Projects/
├── Commun/
│   └── 2026-09-25_Enregistrement/
│       ├── enregistrement.mp3
│       ├── project.sttproj
│       └── transcription.json
├── Projet_A/
└── Projet_B/
```

Lors d’un prétraitement, un fichier audio final optimisé peut également être conservé dans le dossier projet.

## Fichiers projet

Les projets Transcript Studio utilisent l’extension :

```text
.sttproj
```

Le fichier projet contient notamment les données nécessaires à la reconstruction de la transcription :

- informations générales ;
- référence au fichier audio ;
- langue ;
- intervenants ;
- couleurs ;
- mots et horodatages ;
- blocs de parole ;
- réponse issue de la transcription ElevenLabs.

## Thèmes

Trois modes d’affichage sont disponibles :

- Système ;
- Clair ;
- Sombre.

Le mode Système adapte le thème en fonction du mode détecté par l’application.

## Structure générale du projet

```text
TranscriptStudio/
├── architecture/
├── docs/
├── icons/
├── models/
├── services/
├── test/
├── tools/
│   └── ffmpeg/
├── ui/
├── requirements.txt
├── requirements-dev.txt
└── TranscriptStudio.py
```

### `models/`

Modèles de données utilisés pour représenter notamment les projets, intervenants, mots, blocs de transcription et paramètres de traitement audio.

### `services/`

Services techniques et métier :

- gestion des projets et paramètres ;
- intégration avec l’API ElevenLabs ;
- prétraitement audio ;
- FFmpeg ;
- détection et suppression des silences ;
- lecture audio ;
- sauvegarde ;
- export.

### `ui/`

Fenêtres, dialogues et composants graphiques PySide6.

### `icons/`

Ressources graphiques de l’application. Certaines icônes SVG proviennent de Tabler Icons.

### `docs/`

Documentation utilisateur de l’application.

### `tools/ffmpeg/`

Emplacement attendu pour `ffmpeg.exe`. Cet exécutable n'est pas stocké dans le dépôt Git.

## Développement

Les dépendances supplémentaires utilisées pour les tests et certains outils de développement sont déclarées dans :

```text
requirements-dev.txt
```

Installation :

```powershell
python -m pip install -r requirements-dev.txt
```

Le fichier inclut `requirements.txt`, il n’est donc pas nécessaire d’installer les deux séparément dans un environnement de développement neuf.

## Build Windows

La version 1.0 est distribuée sous deux formes, produites depuis les sources du dépôt :

| Artefact | Contenu | Taille | SHA-256 |
| --- | --- | --- | --- |
| `TranscriptStudio-1.0-setup.exe` | Installateur Inno Setup, per-machine (Program Files, raccourcis, désinstallation propre) | 77 Mo | `f3ad4a090c766d885a3c32b142ebf06a4dd1424bc93e416aa0e71d453337399` |
| `TranscriptStudio-1.0-portable.zip` | Archive portable sans installation ni modification du système | 110 Mo | `a1fe5fe51920febb6ba1f8cde717f2ebf0c91e1de952c3157f5ab9417c0b0dd8` |

Les deux artefacts embarquent l’application complète : binaire Nuitka standalone, FFmpeg (`tools/ffmpeg/windows/ffmpeg.exe`), icônes et manuel utilisateur PDF.

### Reproduire le build

Le build nécessite un **CPython 3.11 standard** (une distribution Anaconda/conda ne fonctionne pas : `import ctypes` y provoque un arrêt fatal dans le binaire standalone). Procédure :

```powershell
# 1. Environnement de build propre
uv venv --python 3.11 TranscriptStudio_buildenv
uv pip install --python TranscriptStudio_buildenv/Scripts/python.exe -r requirements.txt nuitka ordered-set zstandard

# 2. Binaire standalone Nuitka (MSVC requis) -> build\TranscriptStudio.dist\
tools\build_windows.bat TranscriptStudio_buildenv\Scripts\python.exe

# 3. Installateur Inno Setup (Inno Setup 6 requis) -> dist\TranscriptStudio-1.0-setup.exe
ISCC.exe tools\installer_windows.iss
```

### Analyse VirusTotal

Analyse du 10/10/2026 sur `TranscriptStudio-1.0-setup.exe` :

- **2 moteurs sur 66** signalent le fichier : Arctic Wolf (`Unsafe`) et Trapmine (`Suspicious.low.ml.score`) ;
- il s’agit de scores heuristiques de machine learning, typiques des faux positifs sur binaires non signés ;
- tous les moteurs majeurs (Microsoft, Kaspersky, ESET, Bitdefender, Avast…) sont **non détectés** ;
- l’analyse complète : `https://www.virustotal.com/gui/file/f3ad4a090c766d885a3c32b142ebf06a4dd1424bc93e416aa0e71d453337399`

L’exécutable n’étant pas signé (pas de certificat de signature de code), Windows SmartScreen peut afficher « Windows a protégé votre PC » au premier lancement d’une nouvelle version. Le contournement (« Informations complémentaires → Exécuter quand même ») est documenté dans le manuel utilisateur (section « Installation »).

## Composants et services tiers

Transcript Studio repose sur plusieurs projets et services tiers qui conservent leurs licences, marques et conditions d’utilisation respectives.

### Tabler Icons

Certaines icônes SVG utilisées dans l’interface proviennent de Tabler Icons.

Tabler Icons est distribué sous licence MIT.

Copyright (c) 2020-2026 Paweł Kuna

Projet :

https://github.com/tabler/tabler-icons

Licence :

https://github.com/tabler/tabler-icons/blob/main/LICENSE

La notice de licence et de copyright de Tabler Icons doit être conservée conformément aux conditions de la licence MIT.

### ElevenLabs

Transcript Studio utilise l’API ElevenLabs Speech-to-Text comme service externe de transcription.

ElevenLabs reste une marque et un service indépendants de Transcript Studio. L’utilisation de son API nécessite un compte et une clé API valides et reste soumise aux conditions du service ElevenLabs.

Transcript Studio n’est ni affilié à, ni sponsorisé, ni approuvé par ElevenLabs.

### FFmpeg

FFmpeg est un projet tiers indépendant de Transcript Studio.

Les binaires FFmpeg et FFprobe ne sont pas redistribués dans le dépôt source. L’utilisateur les télécharge séparément pour son environnement local.

Informations officielles :

https://ffmpeg.org/

https://ffmpeg.org/legal.html

### Dépendances Python

Les bibliothèques Python installées via `requirements.txt` restent soumises à leurs licences respectives. La licence de Transcript Studio ne remplace pas les conditions applicables aux composants tiers.

## Licence de Transcript Studio

Copyright © 2026 David FRECHET

Transcript Studio est destiné à être distribué sous la **GNU General Public License version 3 uniquement (`GPL-3.0-only`)**.

Cette licence autorise notamment l’utilisation, l’étude, la modification et la redistribution du logiciel sous les conditions de la GPLv3. Lorsqu’une version couverte par la GPL est redistribuée, les obligations prévues par cette licence doivent être respectées.

Le texte officiel complet de la GNU GPL version 3 doit être placé dans le fichier `LICENSE` à la racine du dépôt avant une publication publique du projet.

Référence officielle :

https://www.gnu.org/licenses/gpl-3.0.html

Les composants tiers utilisés par Transcript Studio restent soumis à leurs propres licences.

## État du projet

Version affichée actuellement dans l’application :

```text
1.0
Octobre 2026
```

Le dépôt est préparé pour la diffusion des **sources** et du **build Windows 1.0** (installateur et archive portable, voir la section « Build Windows »). La version 1.0 a été validée par :

- build Nuitka standalone reproductible depuis un environnement propre ;
- installation/désinstallation silencieuses de l’installateur (Program Files, raccourcis, registre) ;
- test de fumée du binaire installé ;
- analyse VirusTotal de l’installateur (2/66, faux positifs heuristiques, voir « Build Windows »).

Restent à valider avant diffusion large : analyse VirusTotal de l’archive portable, test sur une machine Windows vierge sans environnement de développement.

## Auteur

David FRECHET

## Avertissement

La transcription automatique peut contenir des erreurs. Le texte et l’attribution des interventions aux différents locuteurs doivent être contrôlés avant utilisation.

Transcript Studio fournit des fonctions de relecture, correction et réaffectation des intervenants afin de faciliter ce contrôle.
