#audio_processing_settings.py
from dataclasses import dataclass


@dataclass
class AudioProcessingSettings:

    #
    # Découpe début
    #

    trim_start_enabled: bool = False
    trim_start_time: float = 0.0

    #
    # Découpe fin
    #

    trim_end_enabled: bool = False
    trim_end_time: float = 0.0

    #
    # Suppression silences
    #

    silence_enabled: bool = False
    silence_threshold_db: float = -40.0
    silence_min_duration: float = 0.5

    #
    # Accélération
    #

    speed_enabled: bool = False
    speed_percent: int = 0