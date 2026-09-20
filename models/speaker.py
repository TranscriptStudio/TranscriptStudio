from dataclasses import dataclass


@dataclass
class Speaker:
    id: str
    name: str
    color: str = "#4A90E2"