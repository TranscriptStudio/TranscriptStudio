import json

from models.project import Project
from models.word import Word
from models.block import Block
from models.speaker import Speaker

DEFAULT_COLORS = [

    # Palette actuelle
    "#4A90E2",  # bleu
    "#50E3C2",  # turquoise
    "#F5A623",  # orange
    "#BD10E0",  # violet
    "#7ED321",  # vert
    "#D0021B",  # rouge
    "#61007F",  # violet profond
    "#02842B",  # vert foncé
    "#34495E",  
    "#F5568B",  
    "#FB5E0A",  
    "#47120A",  
]

def build_speakers(words):
    if not words:

        return [
            Speaker(
                id="speaker_default",
                name="Transcription",
                color=DEFAULT_COLORS[0]
            )
        ]
    
    speakers = []
    speaker_ids = []

    for word in words:

        if word.speaker_id not in speaker_ids:
            speaker_ids.append(word.speaker_id)

    if not speaker_ids:
        speaker_ids = ["speaker_default"]

    for i, speaker_id in enumerate(speaker_ids):

        color = DEFAULT_COLORS[i % len(DEFAULT_COLORS)]

        speakers.append(
            Speaker(
                id=speaker_id,
                name=(
                    "Transcription"
                    if speaker_id == "speaker_default"
                    else speaker_id
                ),
                color=color
            )
        )

    return speakers

def build_blocks(words):

    if not words:
        return []

    blocks = []

    block_id = 1

    current_speaker = words[0].speaker_id
    block_start = 0

    for i, word in enumerate(words):

        if word.speaker_id != current_speaker:

            blocks.append(
                Block(
                    id=block_id,
                    speaker_id=current_speaker,
                    start_word=block_start,
                    end_word=i - 1
                )
            )

            block_id += 1
            block_start = i
            current_speaker = word.speaker_id

    blocks.append(
        Block(
            id=block_id,
            speaker_id=current_speaker,
            start_word=block_start,
            end_word=len(words) - 1
        )
    )

    return blocks

def build_words(raw_words):

    words = []

    for item in raw_words:

        words.append(
            Word(
                text=item["text"],
                start=item["start"],
                end=item["end"],
                speaker_id=item.get(
                    "speaker_id",
                    "speaker_default"
                ),
                item_type=item["type"]
            )
        )

    return words

def import_elevenlabs_json(json_path):

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    words = build_words(data["words"])

    speakers = build_speakers(words)

    blocks = build_blocks(words)

    project = Project(
        name=json_path,
        audio_file="",
        transcription_id=data.get("transcription_id"),
        language_code=data.get("language_code"),
        duration_seconds=data.get("audio_duration_secs", 0),
        speakers=speakers,
        words=words,
        blocks=blocks,
        original_elevenlabs_response=data
    )

    return project