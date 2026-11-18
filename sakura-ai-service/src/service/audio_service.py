import os
import uuid
from pathlib import Path
from dotenv import load_dotenv
from src.logger.logger import SakuraLogger
import assemblyai as aai

load_dotenv()
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

recorder_logger = SakuraLogger("recorder_logger")

UPLOAD_DIR = Path("uploads/audio")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class VoiceRecorder:
    """Stores candidate audio and transcribes it as Japanese with AssemblyAI."""

    def save_audio(
        self, audio_files: bytes, interview_id: str, turn_number: int
    ) -> str:
        """
        Persist the uploaded audio under ``uploads/audio``.

        Returns the local path that the caller can save on the interview turn.
        """

        # name of the file and the file path
        file_name = f"{interview_id}_turn{turn_number}_{uuid.uuid4().hex[:8]}.webm"
        file_path = UPLOAD_DIR / file_name

        # save the audio file in the file path specified
        with open(file_path, "wb") as f:
            f.write(audio_files)

        recorder_logger.info_log(f"Audio saved to path:{file_path}")
        return str(file_path)

    def transcribe_audio(self, audio_path: str):
        """
        Send a saved audio file to AssemblyAI for Japanese transcription.

        Returns the recognized text, or an empty string when transcription fails.
        """
        try:
            recorder_logger.info_log(f"Transcribing:{audio_path}")

            config = aai.TranscriptionConfig(language_code="ja")
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe(audio_path, config=config)
            recorder_logger.info_log(f"Transcript:{transcript}")

            if transcript.status == aai.TranscriptStatus.error:
                recorder_logger.error_log(
                    f"AssemblyAI error in transcribing: {transcript.error}"
                )
                return ""

            recorder_logger.info_log(f"Transcription complete:{len(transcript.text)}")
            return transcript.text
        except Exception as e:
            recorder_logger.error_log(f"Error message:{e}")
            return ""
