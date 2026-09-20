from PySide6.QtCore import (
    QObject,
    Signal,
)

from services.elevenlabs_transcriber import (
    ElevenLabsTranscriber
)


class TranscriptionWorker(QObject):

    finished = Signal(dict)

    error = Signal(str)

    def __init__(
        self,
        audio_file,
        options
    ):
        super().__init__()

        self.audio_file = audio_file
        self.options = options

    def run(self):

        try:

            transcriber = (
                ElevenLabsTranscriber()
            )

            data = (
                transcriber.transcribe(
                    self.audio_file,
                    self.options
                )
            )

            self.finished.emit(data)

        except Exception as e:

            self.error.emit(
                str(e)
            )