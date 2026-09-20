from dataclasses import dataclass
from typing import Optional

@dataclass
class Word:
    text: str
    start: Optional[float]
    end: Optional[float]
    speaker_id: str
    item_type: str # word /spacing
    is_inserted: bool = False
    is_deleted: bool = False