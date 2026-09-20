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

    return project

def save_as_project(project: Project, filename: str):
    if not filename.endswith(".sttproj"):
        filename += ".sttproj"
    save_project(project, filename)
        