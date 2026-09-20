from dataclasses import dataclass, field
from typing import List, Optional

from .speaker import Speaker
from .word import Word
from .block import Block
from models import block

from models.word import Word

@dataclass
class Project:
    """
    Objet racine du projet.
    """

    name: str
    audio_file: str
    project_file: str | None = None
    modified: bool = False
    transcription_id: Optional[str] = None
    language_code: Optional[str] = None
    duration_seconds: float = 0.0

    speakers: List[Speaker] = field(default_factory=list)
    words: List[Word] = field(default_factory=list)
    blocks: List[Block] = field(default_factory=list)

    # Réponse API brute conservée pour ne jamais perdre d'information
    original_elevenlabs_response: dict = field(default_factory=dict)

    def get_speaker_by_id(self, speaker_id: str) -> Optional[Speaker]:
        """
        Retourne le locuteur correspondant à l'ID donné.
        """
        for speaker in self.speakers:
            if speaker.id == speaker_id:
                return speaker
        return None

    def get_block_by_id(self, block_id: int) -> Optional[Block]:
        """
        Retourne le bloc correspondant à l'ID donné.
        """
        for block in self.blocks:
            if block.id == block_id:
                return block
        return None

    def get_block_items(self, block):   
        """
        Retourne la liste des mots du bloc donné.
        """
        return self.words[block.start_word:block.end_word + 1]   

    def get_block_text(self, block):
        """
        Retourne le texte complet du bloc donné.
        """
        items = self.get_block_items(block)
        return "".join(item.text for item in items if not item.is_deleted)

    def get_block_for_word(self, word_index: int):
        """
        Retourne le bloc contenant le mot à l'index donné."""
        for block in self.blocks:
            if block.contains_word(word_index):
                return block
        return None

    def get_block_speaker(self, block):
        """
        Retourne le locuteur du bloc donné.
        """
        return self.get_speaker_by_id(block.speaker_id)

    def add_speaker(self, speaker: Speaker) -> None:
        """
        Ajoute un locuteur au projet.
        """
        self.speakers.append(speaker)

    def add_block(self, block: Block) -> None:
        """
        Ajoute un bloc au projet.
        """
        self.blocks.append(block)

    def remove_block(self, block_id: int) -> None:
        """
        Supprime un bloc du projet.
        """ 
        self.blocks = [
            block
            for block in self.blocks
            if block.id != block_id
        ]

    def get_speaker_names(self) -> list[str]:
        """
        Retourne la liste des noms de tous les locuteurs du projet.
        """
        return [speaker.name for speaker in self.speakers]
    
    def generate_speaker_id(self) -> str:
        """
        Génère un ID unique pour un nouveau locuteur.
        """
        return f"speaker_{len(self.speakers)}"

    def find_word_at_time(
        self,
        current_time
    ):

        last_word = None

        for index, word in enumerate(self.words):
            if word.is_inserted:
                continue
            if word.item_type == "spacing":
                continue

            if word.start <= current_time <= word.end:
                return index

            if word.start <= current_time:
                last_word = index

        return last_word

    def on_speaker_changed(
        self,
        block_id,
        speaker_name
    ):

        block = (
            self.project
            .get_block_by_id(
                block_id
            )
        )

        if not block:
            return

        speaker = (
            self.project
            .get_speaker_by_name(
                speaker_name
            )
        )

        if not speaker:
            return

        block.speaker_id = speaker.id

    def split_block(
        self,
        block_id,
        word_index
    ):

        block = self.get_block_by_id(
            block_id
        )

        if block is None:
            return

        if word_index <= block.start_word:
            return

        if word_index > block.end_word:
            return

        new_block_id = (
            max(
                b.id
                for b in self.blocks
            ) + 1
        )

        new_block = Block(
            id=new_block_id,
            speaker_id=block.speaker_id,
            start_word=word_index,
            end_word=block.end_word,
            created_by_user=True
        )

        block.end_word = (
            word_index - 1
        )

        index = self.blocks.index(
            block
        )

        self.blocks.insert(
            index + 1,
            new_block
        )

    def split_block_after(
        self,
        block_id,
        word_index
    ):

        self.split_block(
            block_id,
            word_index + 1
        )

    def merge_blocks(
        self,
        first_block_id,
        second_block_id
    ):

        block1 = self.get_block_by_id(
            first_block_id
        )

        block2 = self.get_block_by_id(
            second_block_id
        )

        if block1 is None:
            return False

        if block2 is None:
            return False

        #
        # même intervenant uniquement
        #
        if block1.speaker_id != block2.speaker_id:
            return False

        block1.end_word = block2.end_word

        self.blocks.remove(
            block2
        )

        return True

    def replace_word_text(
        self,
        word_index,
        new_text
    ):

        self.words[word_index].text = new_text

    def delete_word(
        self,
        word_index
    ):

        self.words[word_index].is_deleted = True

    def insert_word_before(
        self,
        word_index,
        text
    ):

        reference_word = self.words[word_index]

        inserted_word = Word(
            text=text,
            start=None,
            end=None,
            speaker_id=reference_word.speaker_id,
            item_type="word",
            is_inserted=True
        )

        self.words.insert(
        word_index,
        inserted_word
    )

    def mark_modified(self):

        self.modified = True

    def mark_saved(self):

        self.modified = False

    @property
    def is_diarized(self):

        return not (
            len(self.speakers) == 1
            and self.speakers[0].id == "speaker_default"
        )

    def is_speaker_used(
        self,
        speaker_id
    ):

        return any(

            block.speaker_id == speaker_id

            for block in self.blocks
        )

    def remove_speaker(
        self,
        speaker_id
    ):

        if self.is_speaker_used(
            speaker_id
        ):
            return False

        self.speakers = [

            speaker

            for speaker in self.speakers

            if speaker.id != speaker_id

        ]

        return True