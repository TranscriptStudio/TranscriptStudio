from dataclasses import dataclass


@dataclass
class AudioProcessingSettings:

    cut_before_enabled: bool = False

    cut_before_seconds: float = 0.0

    remove_silence_enabled: bool = False

    silence_threshold_db: float = -40.0

    silence_min_duration: float = 0.5

    keep_silence_duration: float = 0.1

    speed_enabled: bool = False

    speed_percent: int = 50