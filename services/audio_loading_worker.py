# audio_loading_worker.py

from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
)

from services.audio_waveform_service import (
    AudioWaveformService
)


class AudioLoadingWorker(QObject):

    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        audio_file
    ):
        super().__init__()

        self.audio_file = audio_file

    @Slot()
    def run(self):
        try:
            document = (
                AudioWaveformService()
                .extract_waveform(
                    self.audio_file
                )
            )

            self.finished.emit(
                document
            )

        except Exception as e:
            self.error.emit(
                str(e)
            )