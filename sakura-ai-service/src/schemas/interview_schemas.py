from pydantic import BaseModel
from typing import Optional


# ------------------------------------------------------------------ #
#  Request models                                                      #
# ------------------------------------------------------------------ #

class StartInterviewRequest(BaseModel):
    scenario_id: str
    candidate_id: str


class UpdateInterviewStatusRequest(BaseModel):
    status: str  # only "abandoned" is currently supported (candidate quits early)


# ------------------------------------------------------------------ #
#  Response models                                                     #
# ------------------------------------------------------------------ #

class StartInterviewResponse(BaseModel):
    status: str
    interview_id: str
    question_text: str
    turn_number: int


class AnswerResponse(BaseModel):
    status: str
    interview_id: str
    transcript: str
    next_question: Optional[str]   # None when interview is complete
    turn_number: int
    is_complete: bool


class QuestionResponse(BaseModel):
    status: str
    question_text: str
    turn_number: int


class EndInterviewResponse(BaseModel):
    status: str
    interview_id: str
