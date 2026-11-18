from fastapi import APIRouter, UploadFile, File
from src.exception.exception import raise_exception
from fastapi.responses import JSONResponse
from src.service.audio_service import VoiceRecorder
from src.logger.logger import SakuraLogger
from src.constants.constants import SUCCESS, FAILED

voice_recorder = VoiceRecorder()
audio_router = APIRouter(prefix="/audio")
audio_logger = SakuraLogger("audio_logger")


@audio_router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(..., description="Candidate should upload the audio file"),
    interview_id: str = "test",
    turn_number: int = 0,
):
    """Standalone audio transcription endpoint for trying the Japanese STT flow.

    Accepts multipart audio plus optional interview and turn identifiers. Saves
    the audio and returns its path and Japanese transcript; it does not advance
    an interview or store a VoiceExchange row.
    """
    audio_logger.info_log(f"Audio upload recieved:{interview_id}-{turn_number}")
    audio_types = {"audio/webm", "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg"}
    base_type = (audio.content_type or "").split(";")[0].strip().lower()
    if base_type not in audio_types:
        audio_logger.error_log(f"content-type not supported:{audio.content_type}")
        raise raise_exception(
            status_code=415,
            detail=f"Unsupported audio type:{audio.content_type}, supported types:{','.join(audio_types)} ",
        )
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise raise_exception(status_code=400, detail="Empty audio file recieved")

        audio_path = voice_recorder.save_audio(audio_bytes, interview_id, turn_number)
        transcript = voice_recorder.transcribe_audio(audio_path)

        return JSONResponse(
            status_code=200,
            content={
                "status": SUCCESS,
                "interview_id": interview_id,
                "turn_number": turn_number,
                "audio_path": audio_path,
                "transcript": transcript,
            },
        )

    except raise_exception:
        raise
    except Exception as e:
        audio_logger.error_log(f"Audio processing failed {e}")
        raise raise_exception(status_code=500, detail=FAILED)
