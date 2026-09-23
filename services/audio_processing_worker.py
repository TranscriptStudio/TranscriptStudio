# audio_processing_worker.py
 
from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
)

from services.audio_processing_pipeline import (
    AudioProcessingPipeline
)

from services.audio_waveform_service import (
    AudioWaveformService
)


class AudioProcessingWorker(QObject):

    progress = Signal(
        int,
        str
    )

    finished = Signal(
        object,
        object
    )

    error = Signal(str)

    def __init__(
        self,
        audio_file,
        processing_wav,
        settings,
        output_file
    ):
        super().__init__()

        self.audio_file = audio_file
        self.processing_wav = processing_wav
        self.settings = settings
        self.output_file = output_file

    @Slot()
    def run(self):

        try:

            pipeline = AudioProcessingPipeline(
                self.audio_file,
                self.processing_wav,
                self.settings,
                self.output_file,
                progress_callback=(
                    self.report_progress
                )
            )

            output_file = pipeline.run()

            self.progress.emit(
                85,
                "Préparation du résultat..."
            )

            document = (
                AudioWaveformService()
                .extract_waveform(
                    output_file
                )
            )

            self.progress.emit(
                100,
                "Traitement terminé"
            )

            self.finished.emit(
                output_file,
                document
            )

        except Exception as e:

            self.error.emit(
                str(e)
            )

    def report_progress(
        self,
        value,
        message
    ):
        self.progress.emit(
            value,
            message
        )