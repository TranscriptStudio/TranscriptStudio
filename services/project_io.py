import json

from models.project import Project
from models.speaker import Speaker
from models.word import Word
from models.block import Block


def save_project(project: Project, filename: str) -> None:
    """
    Sauvegarde un projet au format JSON.
    """

    data = {
        "name": project.name,
        "audio_file": project.audio_file,
        "transcription_id": project.transcription_id,
        "language_code": project.language_code,
        "duration_seconds": project.duration_seconds,
        "project_file": project.project_file,
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
    """

    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

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
                
    project = Project(
        project_file=data.get("project_file"),
        modified=data.get("modified", False),
        name=data["name"],  
        audio_file=data["audio_file"],
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
        )
    )
    if not project.project_file:
        project.project_file = filename
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
        