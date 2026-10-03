import json
from pathlib import Path

from models.project import Project
from models.speaker import Speaker
from models.word import Word
from models.block import Block


def _normalize_path_for_json(path_str: str) -> str:
    """
    Normalise un chemin pour stockage JSON.
    - Remplace les backslashes Windows par des slashes (compatible toutes plateformes)
    - Conserve les chemins relatifs ou absolus tels quels (sauf normalisation des séparateurs)
    """
    if path_str is None:
        return None
    # Normaliser tous les séparateurs en /
    return path_str.replace("\\", "/")


def _make_relative_path(audio_path: str, project_dir: Path) -> str:
    """
    Convertit un chemin audio en chemin relatif par rapport au dossier du projet.
    
    Si l'audio est dans le dossier projet ou un sous-dossier, retourne un chemin relatif.
    Sinon, retourne le chemin original (absolu ou externe).
    
    Args:
        audio_path: Chemin de l'audio (absolu ou relatif)
        project_dir: Répertoire contenant le fichier .sttproj
        
    Returns:
        Chemin relatif si l'audio est dans le projet, chemin original sinon
    """
    if not audio_path:
        return audio_path
        
    audio_path_obj = Path(audio_path)
    
    # Si c'est déjà un chemin relatif, vérifier s'il existe par rapport à project_dir
    if not audio_path_obj.is_absolute():
        # Test si le chemin relatif pointe vers un fichier dans le dossier projet
        test_path = project_dir / audio_path_obj
        if test_path.exists():
            return _normalize_path_for_json(str(audio_path_obj))
        # Sinon, retourner tel quel
        return _normalize_path_for_json(audio_path)
    
    # Si c'est un chemin absolu, essayer de le rendre relatif
    try:
        # Résoudre le chemin pour éliminer les .. et .
        resolved_audio = audio_path_obj.resolve()
        resolved_project = project_dir.resolve()
        
        # Vérifier si l'audio est dans le dossier projet
        if resolved_audio.parent == resolved_project or resolved_project in resolved_audio.parents:
            # Calculer le chemin relatif
            relative = resolved_audio.relative_to(resolved_project)
            return _normalize_path_for_json(str(relative))
        else:
            # Media externe au dossier projet - garder absolu pour l'instant
            # (Migration future vers chemin relatif si l'utilisateur déplace le fichier)
            return _normalize_path_for_json(audio_path)
    except (ValueError, OSError):
        # Si relative_to échoue ou autre problème, retourner l'original
        return _normalize_path_for_json(audio_path)


def save_project(project: Project, filename: str) -> None:
    """
    Sauvegarde un projet au format JSON.
    
    Pour P1.1 :
    - N'écrit PAS project_file dans le JSON (uniquement en mémoire)
    - Convertit audio_file en chemin relatif si possible
    - Utilise des / pour les chemins (compatible Windows)
    - Ajoute project_format_version
    """
    project_path = Path(filename)
    project_dir = project_path.parent

    # Convertir audio_file en chemin relatif pour la sauvegarde
    relative_audio_file = _make_relative_path(project.audio_file, project_dir)

    data = {
        "project_format_version": project.project_format_version,
        "name": project.name,
        "audio_file": relative_audio_file,
        "transcription_id": project.transcription_id,
        "language_code": project.language_code,
        "duration_seconds": project.duration_seconds,
        # NE PAS SAUVEGARDER project_file dans le JSON (uniquement en mémoire)
        "modified": project.modified,
        "speakers": [
            {
                "id": speaker.id,
                "name": speaker.name,
                "color": speaker.color
            }
            for speaker in project.speakers
        ],

        "words": [
            {
                "text": word.text,
                "start": word.start,
                "end": word.end,
                "speaker_id": word.speaker_id,
                "item_type": word.item_type
            }
            for word in project.words
        ],

        "blocks": [
            {
                "id": block.id,
                "speaker_id": block.speaker_id,
                "start_word": block.start_word,
                "end_word": block.end_word,
                "created_by_user": block.created_by_user
            }
            for block in project.blocks
        ],

        "original_elevenlabs_response":
            project.original_elevenlabs_response
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


def repair_project_speakers(
    speakers,
    blocks
):
    """
    Vérifie la cohérence entre les intervenants
    et les blocs d'un ancien projet.

    Les blocs dont l'intervenant est :
    - absent ;
    - associé à un ID vide ;
    - associé à un intervenant sans nom ;

    sont réaffectés à un intervenant générique.

    Retourne un rapport de réparation ou None.
    """

    generic_name = (
        "Intervenant non identifié"
    )

    #
    # Intervenants considérés comme valides.
    #
    valid_speakers = {
        speaker.id: speaker
        for speaker in speakers
        if (
            speaker.id
            and str(speaker.id).strip()
            and speaker.name
            and str(speaker.name).strip()
        )
    }

    #
    # Chercher les blocs dont l'association
    # à un intervenant n'est pas valide.
    #
    invalid_blocks = []

    for block in blocks:
        speaker = valid_speakers.get(
            block.speaker_id
        )

        if speaker is None:
            invalid_blocks.append(
                block
            )

    #
    # Projet déjà cohérent.
    #
    if not invalid_blocks:
        return None

    #
    # Chercher si l'intervenant générique
    # existe déjà.
    #
    generic_speaker = next(
        (
            speaker
            for speaker in speakers
            if (
                speaker.name
                and speaker.name.strip()
                == generic_name
            )
        ),
        None
    )

    #
    # Sinon le créer avec un ID garanti
    # unique dans le projet.
    #
    if generic_speaker is None:
        existing_ids = {
            speaker.id
            for speaker in speakers
        }

        base_id = (
            "speaker_unidentified"
        )
        generic_id = base_id
        counter = 1

        while generic_id in existing_ids:
            generic_id = (
                f"{base_id}_{counter}"
            )
            counter += 1

        generic_speaker = Speaker(
            id=generic_id,
            name=generic_name,
            color="#808080"
        )

        speakers.append(
            generic_speaker
        )

    #
    # Réaffecter uniquement les blocs
    # réellement incohérents.
    #
    repaired_block_ids = []

    for block in invalid_blocks:
        block.speaker_id = (
            generic_speaker.id
        )

        repaired_block_ids.append(
            block.id
        )

    return {
        "generic_name": (
            generic_speaker.name
        ),
        "generic_id": (
            generic_speaker.id
        ),
        "repaired_blocks": (
            repaired_block_ids
        ),
        "count": (
            len(repaired_block_ids)
        ),
    }


def load_project(filename: str) -> Project:
    """
    Recharge un projet sauvegardé.
    
    Pour P1.1 + P1.2 :
    - Fix project.project_file = Path(filename).resolve() en mémoire
    - Si audio_file est relatif, le résoudre depuis Path(filename).parent
    - Si audio_file est absolu et existe, accepter l'ancien projet
    - Si audio_file absolu n'existe pas, rechercher dans le dossier projet
    - Ne JAMAIS résoudre un media relativement au projects_root global
    """

    project_path = Path(filename)
    project_dir = project_path.parent

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Charger les données de base
    speakers = [
        Speaker(
            id=s["id"],
            name=s["name"],
            color=s["color"]
        )
        for s in data["speakers"]
    ]

    words = [
        Word(
            text=w["text"],
            start=w["start"],
            end=w["end"],
            speaker_id=w["speaker_id"],
            item_type=w["item_type"]
        )
        for w in data["words"]
    ]

    blocks = [
        Block(
            id=b["id"],
            speaker_id=b["speaker_id"],
            start_word=b["start_word"],
            end_word=b["end_word"],
            created_by_user=b.get(
                "created_by_user",
                False
            )
        )
        for b in data["blocks"]
    ]
    
    repair_report = (
        repair_project_speakers(
            speakers,
            blocks
        )
    )

    #
    # Compatibilité avec certains anciens projets :
    # un bloc pouvait être enregistré avec un
    # speaker_id vide ou devenu invalide.
    #
    valid_speaker_ids = {
        speaker.id
        for speaker in speakers
    }

    fallback_speaker_id = (
        speakers[0].id
        if speakers
        else None
    )

    if fallback_speaker_id is not None:
        for block in blocks:
            if block.speaker_id not in valid_speaker_ids:
                block.speaker_id = fallback_speaker_id
                
    # Charger audio_file - P1.2 : Résolution robuste des chemins audio
    audio_file = data.get("audio_file", "")
    
    # P1.2 : Résoudre le chemin audio selon son type
    # 1. Si audio_file est vide, garder vide
    # 2. Si audio_file est un chemin relatif (avec / ou \), le résoudre depuis project_dir
    # 3. Si audio_file est absolu et existe, l'accepter (ancien projet)
    # 4. Si audio_file est absolu et N'EXISTE PAS, rechercher dans project_dir
    if audio_file:
        audio_path_obj = Path(audio_file)
        
        # Normaliser : remplacer / par le séparateur du système
        # Les chemins JSON utilisent /, mais Path gère les deux
        if not audio_path_obj.is_absolute():
            # Chemin relatif - résoudre depuis le dossier du projet
            audio_path_resolved = project_dir / audio_path_obj
            audio_file = str(audio_path_resolved.resolve())
        else:
            # Chemin absolu - vérifier s'il existe
            if not audio_path_obj.exists():
                # Essayer de trouver un fichier de même nom dans le dossier projet
                # Extraire juste le nom de fichier
                filename_only = audio_path_obj.name
                potential_path = project_dir / filename_only
                if potential_path.exists():
                    audio_file = str(potential_path.resolve())
                # Sinon, garder le chemin original (même s'il n'existe pas)
                # L'utilisateur devra le relocaliser manuellement
    
    # Récupérer project_file depuis le JSON s'il existe (compatibilité ancien format)
    legacy_project_file = data.get("project_file")
    
    # Récupérer project_format_version (default à 1 si absent pour compatibilité)
    project_format_version = data.get("project_format_version", 1)
    
    project = Project(
        project_file=legacy_project_file,  # Peut être None pour les nouveaux projets
        modified=data.get("modified", False),
        name=data["name"],  
        audio_file=audio_file,
        transcription_id=data.get(
            "transcription_id"
        ),
        language_code=data.get(
            "language_code"
        ),
        duration_seconds=data.get(
            "duration_seconds",
            0
        ),
        speakers=speakers,
        words=words,
        blocks=blocks,
        original_elevenlabs_response=data.get(
            "original_elevenlabs_response",
            {}
        ),
        project_format_version=project_format_version
    )
    
    # P1.1 : TOUJOURS définir project.project_file en mémoire avec le chemin absolu
    # Cela permet la sauvegarde, autosave, titre et export
    if not project.project_file:
        project.project_file = str(project_path.resolve())
    
    #
    # Rapport transitoire utilisé uniquement
    # pour informer l'utilisateur après
    # l'ouverture d'un ancien projet réparé.
    #
    project.speaker_repair_report = (
        repair_report
    )
    return project


def save_as_project(project: Project, filename: str):
    if not filename.endswith(".sttproj"):
        filename += ".sttproj"
    save_project(project, filename)
