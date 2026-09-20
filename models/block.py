from dataclasses import dataclass

@dataclass
class Block:

    id: int

    speaker_id: str

    start_word: int

    end_word: int

    created_by_user: bool = False

    def contains_word(self, word_index: int):

        return (
            self.start_word
            <= word_index
            <= self.end_word
        )