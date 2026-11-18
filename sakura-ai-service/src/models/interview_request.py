from pydantic import BaseModel
from typing import Optional


class InterviewRequest(BaseModel):
    scenario_id: Optional[str] = None
    candidate_id: Optional[str] = None
    interview_id: Optional[str] = None


class InterviewResponses(BaseModel):
    interview_id: Optional[str] = None
    question_text: Optional[str] = None
    turn_number: Optional[int] = None
    next_question: Optional[str] = None
    feedback: Optional[str] = None
    is_complete: Optional[bool] = True
