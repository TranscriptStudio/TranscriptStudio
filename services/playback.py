from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import (QMediaPlayer, QAudioOutput)
from PySide6.QtCore import QUrl


class PlaybackManager(QObject):

    # temps courant en secondes
    position_changed = Signal(float)

    # durée totale en secondes
    duration_changed = Signal(float)

    # état lecture / pause
    playing_changed = Signal(bool)

    def __init__(self):
        super().__init__()

        self.audio_output = QAudioOutput()

        self.player = QMediaPlayer()
        self.player.setAudioOutput(
            self.audio_output
        )

        self.player.positionChanged.connect(
            self._on_position_changed
        )

        self.player.durationChanged.connect(
            self._on_duration_changed
        )

        self.player.playbackStateChanged.connect(
            self._on_state_changed
        )

    # -----------------------
    # Chargement audio
    # -----------------------

    def load_file(self, filename: str):

        self.player.setSource(
            QUrl.fromLocalFile(filename)
        )
        
    def unload(self):
        self.player.stop()
        self.player.setSource(
            QUrl()
        )
    # -----------------------
    # Lecture
    # -----------------------

    def play(self):
        
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def toggle_play_pause(self):
        
        if self.is_playing():   
            self.pause()
        else:
            self.play()

    # -----------------------
    # Position
    # -----------------------

    def set_position(self, seconds: float):

        self.player.setPosition(
            int(seconds * 1000)
        )

    def get_position(self) -> float:

        return (
            self.player.position()
            / 1000
        )

    def get_duration(self) -> float:

        return (
            self.player.duration()
            / 1000
        )

    # -----------------------
    # Etat
    # -----------------------

    def is_playing(self) -> bool:

        return (
            self.player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        )

    # -----------------------
    # Volume
    # -----------------------

    def set_volume(self, volume: int):
        """
        volume entre 0 et 100
        """

        self.audio_output.setVolume(
            volume / 100
        )

    # -----------------------
    # Signaux internes
    # -----------------------

    def _on_position_changed(self, position_ms):

        self.position_changed.emit(
            position_ms / 1000
        )

    def _on_duration_changed(self, duration_ms):

        self.duration_changed.emit(
            duration_ms / 1000
        )

    def _on_state_changed(self, state):

        playing = (
            state
            == QMediaPlayer.PlaybackState.PlayingState
        )

        self.playing_changed.emit(
            playing
        )

    def jump_forward(self, seconds: float = 5):
        self.set_position(self.get_position()+ seconds)


    def jump_backward(self, seconds: float = 5):
        self.set_position(max(0,self.get_position() - seconds))