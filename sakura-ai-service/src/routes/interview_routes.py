from fastapi import APIRouter, UploadFile, HTTPException
from fastapi.param_functions import Form, File
from fastapi.responses import JSONResponse
from src.models.interview_request import InterviewRequest
from src.logger.logger import SakuraLogger
from src.service.audio_service import VoiceRecorder
from src.service.interview_service import InterviewService
from src.constants.constants import SUCCESS, FAILED

interview_api_logger = SakuraLogger("interview-api-router")
voice_recorder = VoiceRecorder()
interview_service = InterviewService()
interview_router = APIRouter(prefix="/interview")


# ------------------------------------------------------------------ #
#  POST /interview/start                                              #
# ------------------------------------------------------------------ #
@interview_router.post("/start")
def start_interview(request: InterviewRequest):
    """
    Start an AI-led interview.

    **Request JSON:** `scenario_id` and `candidate_id`.
    **Success response:** interview ID, AI-generated opening question, and turn number.
    Requires a valid scenario, database connection, and configured LLM credentials.
    """
    try:
        result = interview_service.start_interview(
            request.scenario_id, request.candidate_id
        )
        interview_api_logger.info_log(
            f"Interview session created: {result.interview_id}"
        )
        return JSONResponse(
            status_code=200,
            content={"status": SUCCESS, **result.model_dump()},
        )

    except Exception as e:
        interview_api_logger.error_log(f"Start interview failed : {e}")
        raise HTTPException(status_code=500, detail=FAILED)


# ------------------------------------------------------------------ #
#  POST /interview/{interview_id}/answer                              #
# ------------------------------------------------------------------ #


@interview_router.post("/{interview_id}/answer")
async def submit_answer(
    interview_id: str,
    audio: UploadFile = File(..., description="Candidate audio recording"),
    turn_number: int = Form(...),
):
    """
    Submit one recorded answer and continue the AI-led interview.

    Send multipart form data with an `audio` file and integer `turn_number`.
    The endpoint saves the audio, transcribes Japanese speech with AssemblyAI,
    stores the transcript, and asks the interview AI to provide coaching and a
    relevant next question. The response includes the transcript, feedback,
    next question, next turn number, and whether the interview is complete.
    """
    audio_types = {"audio/webm", "audio/wav", "audio/mpeg", "audio/mp4", "audio/ogg"}
    base_type = (audio.content_type or "").split(";")[0].strip().lower()
    if base_type not in audio_types:
        raise HTTPException(
            status_code=415, detail=f"Unsupported audio type: {audio.content_type}"
        )
    try:
        # 1. Save audio to disk
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        audio_path = voice_recorder.save_audio(audio_bytes, interview_id, turn_number)
        interview_api_logger.info_log(
            f"Audio saved for the interview={interview_id} and turn number:{turn_number}"
        )

        # 2. Transcribe via AssemblyAI
        transcript = voice_recorder.transcribe_audio(audio_path)
        interview_api_logger.info_log(
            f"Transcript length={len(transcript)} interview={interview_id}"
        )

        # 3. Submit answer — get next question
        result = interview_service.submit_answer(
            interview_id=interview_id,
            transcript=transcript,
            audio_path=audio_path,
            turn_number=turn_number,
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": SUCCESS,
                "interview_id": interview_id,
                "transcript": transcript,
                **result.model_dump(),
            },
        )

    except ValueError as e:
        interview_api_logger.error_log(f"Failed to submit answer:{e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        interview_api_logger.error_log(f"Unexpected error on answer:{e}")
        raise HTTPException(status_code=500, detail=FAILED)


# ------------------------------------------------------------------ #
#  GET /interview/{interview_id}/question                             #
# ------------------------------------------------------------------ #
@interview_router.get("/{interview_id}/question")
def get_current_question(interview_id: str):
    """Return the active interview's current manager question and turn number."""
    try:
        result = interview_service.get_current_question(interview_id)
        return JSONResponse(
            status_code=200,
            content={"status": SUCCESS, **result.model_dump()},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ------------------------------------------------------------------ #
#  POST /interview/{interview_id}/end                                 #
# ------------------------------------------------------------------ #


@interview_router.post("/{interview_id}/end")
def end_interview(interview_id: str):
    """End an active interview early and mark it as abandoned in the database."""
    try:
        interview_service.end_interview(interview_id)
        return JSONResponse(
            status_code=200,
            content={"status": SUCCESS, "interview_id": interview_id},
        )
    except Exception as e:
        interview_api_logger.error_log(f"Failed to end interview:{interview_id}")
        raise HTTPException(status_code=500, detail=FAILED)
