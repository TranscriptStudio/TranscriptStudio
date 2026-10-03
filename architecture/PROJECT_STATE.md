# PROJECT_STATE.md - Etat actuel du développement TranscriptStudio

> **Dernière mise à jour** : 2026-10-03
> **Commit actuel** : 7a2a2c4
> **Branche** : master

---

## 📊 ETAT GIT

### Position actuelle
- **Branche** : master
- **Local vs Origin** : +3 commits (en avance sur origin/master)
- **Dernier commit** : `7a2a2c4 Commit P0-2 - API capability decoupling`
- **Commits précédents** :
  - `b08698e P0.1 First-run + Decouplage API + FFmpeg minimal`
  - `5f6ea5f readme file and new roadmap`

### Fichiers non suivis (untracked)
- `.vibe/` (dossier de configuration Vibe)
- `architecture/AGENTS.md` (instructions agent)

### Modifications non commitées
- Aucune

---

## 🎯 ETAT DU DEVELOPPEMENT

### Phases Complétées

#### ✅ **P0.1 - First-Run Minimal** (VALIDÉ)
- **Statut** : Complété et testé
- **Commit** : b08698e
- **Fonctionnalités** :
  - Configuration initiale obligatoire au premier lancement
  - Choix explicite du répertoire projets
  - Proposition du chemin `Documents/Projets Transcript Studio`
  - Clé API facultative pour le démarrage
  - 3 fixes supplémentaires appliqués après validation initiale

#### ✅ **P0.2 - Découplage Clé API / Capacités** (IMPLEMENTE)
- **Statut** : Implémenté et commité
- **Commit** : 7a2a2c4
- **Fonctionnalités** :
  - Création de `services/api_capabilities.py` avec fonctions centrales :
    - `has_api_key()`
    - `has_transcription_api()`
    - `can_transcribe_direct()`
    - `can_finalize_audio()` (toujours True)
    - `can_access_account_info()`
  - Mise à jour de `services/elevenlabs_api.py` : vérification de la clé API à l'initialisation
  - Mise à jour de `ui/elevenlabs_account_dialog.py` : vérification avant appel API
  - Mise à jour de `ui/transcription_entry_dialog.py` : 
    - Désactivation de l'option transcription directe sans API
    - Message informatif si l'utilisateur essaie de sélectionner la transcription directe
    - Tooltip mis à jour pour expliquer la raison

### Phases en cours
- Aucune phase actuellement en cours d'implémentation

#### ✅ **P0.3 - FFmpeg Multiplateforme Minimal** (IMPLEMENTE)
- **Statut** : Implémenté et commité
- **Commit** : fd615c9
- **Fonctionnalités** :
  - Remplacement de la constante Windows-only par un resolveur multiplateforme
  - `FFMPEG_NAME = "ffmpeg.exe"` sur Windows, `"ffmpeg"` sur macOS/Linux
  - `FFMPEG_PATH` utilise maintenant `FFMPEG_NAME`
  - Fonction `get_ffmpeg_path()` avec fallback vers PATH
  - Mise à jour de `validate_ffmpeg_tools()` avec vérification PATH et messages clairs

#### ✅ **P1.1 - Définir le contrat du format projet** (IMPLEMENTE)
- **Statut** : Implémenté et testé
- **Fichiers concernés** : `models/project.py`, `services/project_io.py`
- **Fonctionnalités** :
  - Ajout de `project_format_version: 1` au modèle Project
  - `project_file` **n'est plus sauvegardé** dans le JSON des nouveaux projets
  - `audio_file` est converti en chemin relatif lors de la sauvegarde (si dans dossier projet)
  - Utilisation de `/` pour les chemins JSON (compatible Windows)
  - `Project.project_file` reste **uniquement en mémoire** pour sauvegarde/autosave/titre/export
  - Gestion des médias externes au dossier projet (gardés en absolu pour l'instant)

### Phases en cours
- P1.2 - Résolution à l'ouverture

### Phases Suivantes (selon roadmap)
1. **P1 - PORTABILITE DES PROJETS**
   - P1.2 - Résolution à l'ouverture (chemins relatifs)
   - P1.3 - Migration non-destructive des anciens projets
   - P1.4 - Sauvegarde et autosave après déplacement

---

## 🔍 ECARTS AVEC LA ROADMAP

### Validations à effectuer
- ⏳ P0.2 nécessite des **tests manuels** pour confirmer :
  - Démarrage sans clé → pas d'erreur (implémenté mais non testé)
  - Tentative de transcription directe → message clair, aucune requête HTTP (implémenté mais non testé)
  - Ajout d'une clé depuis Paramètres → transcription disponible sans redémarrage (implémenté mais non testé)

### Points à noter
- P0.1 est marqué comme **VALIDE** dans le roadmap, avec des tests manuels validés
- P0.2 est **implémenté** mais nécessite une validation par tests manuels
- Aucun test automatisé n'existe actuellement pour P0.1 ou P0.2

---

## 🧪 TESTS

### Tests existants
- **Fichier** : `test/test.py`
- **Contenu** : Exemple basique pyqtgraph, **pas une suite de tests fonctionnels**
- **Statut** : Non pertinent pour la validation du projet

### Tests automatisés
- **État** : Aucun test automatisé (pytest) n'existe actuellement
- **Prévu** : Phase P7 (Tests automatisés) dans le roadmap

### Tests manuels recommandés pour P0.2
1. Démarrer l'application avec `settings.json` vide ou sans `elevenlabs_api_key`
2. Vérifier que l'application démarre sans erreur
3. Tenter d'accéder à "Compte ElevenLabs" → devrait afficher message informatif
4. Tenter de créer une nouvelle transcription en mode direct → devrait basculer vers prétraitement
5. Ajouter une clé API valide dans les paramètres
6. Vérifier que la transcription directe devient disponible
7. Vérifier que le compte ElevenLabs devient accessible

---

## 🚀 PROCHAINE ETAPE RECOMMANDEE

### Priorité immédiate
**Valider P1.1 par tests manuels** avant de passer à P1.2

### Si P1.1 est validé
**Passer à P1.2 - Résolution à l'ouverture**
- Fix project.project_file en mémoire avec filename
- Si audio_file est relatif, le résoudre depuis le dossier du .sttproj
- Gérer les anciens projets avec chemins absolus

### Alternative
Si des problèmes sont trouvés lors des tests P1.1, les corriger d'abord.

---

## 📋 RESUME DES COMMITS RECENTS

| Commit | Message | Statut |
|--------|---------|--------|
| HEAD | P1.1 - Portable project format v1 | ⏳ En cours |
| fd615c9 | P0.3 - Minimal cross-platform FFmpeg resolver | ✅ Implémenté |
| 7a2a2c4 | Commit P0-2 - API capability decoupling | ✅ Implémenté |
| b08698e | P0.1 First-run + Decouplage API + FFmpeg minimal | ✅ Validé |
| 5f6ea5f | readme file and new roadmap | ✅ Documentation |

---

## 🎯 DEFINITION OF DONE ACTUELLE

### Pour que P0 soit considéré comme terminé
- [x] P0.1 : First-run fonctionnel et validé
- [x] P0.2 : Découplage API implémenté et validé
- [x] P0.3 : FFmpeg multiplateforme minimal implémenté

**P0 global** : **Terminé** (3/3 sous-phases complétées)

### Pour que P1 soit considéré comme terminé
- [x] P1.1 : Définir le contrat du format projet
- [ ] P1.2 : Résolution à l'ouverture
- [ ] P1.3 : Migration non-destructive des anciens projets
- [ ] P1.4 : Sauvegarde et autosave après déplacement

**P1 global** : **En cours** (1/4 sous-phases complétées)

---

*Ce fichier doit être mis à jour après chaque étape significative du développement.*