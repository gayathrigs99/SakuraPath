import uuid
from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from src.models.shared_base import shared_base
from src.enums.level_and_comp_status import (
    LanguageLevel,
    ReadinessLevel,
    CompletionStatus,
)


class ProgressSummary(shared_base):
    __tablename__ = "progress_summary"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    total_scenarios_completed = Column(Integer)
    current_level = Column(Enum(LanguageLevel))
    days_trained = Column(Integer)
    avg_grammar_score = Column(Integer)
    avg_politeness_score = Column(Integer)
    weak_areas = Column(JSON)
    job_readiness_percentage = Column(Integer)


class UsersScore(shared_base):
    __tablename__ = "user_scores"

    score_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("sakura_users.user_id"))
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("sakura_scenarios.scenario_id"))
    grammar_score = Column(Integer)
    politeness_score = Column(Integer)
    clarity_score = Column(Integer)
    cultural_correctness_score = Column(Integer)
    overall_score = Column(Integer)
    job_readiness_level = Column(Enum(ReadinessLevel))
    created_at = Column(DateTime)


class VoiceInterview(shared_base):
    __tablename__ = "voice_interview"

    interview_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("sakura_users.user_id"))
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("sakura_scenarios.scenario_id"))
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    status = Column(
        Enum(CompletionStatus, name="completion_status_options"),
        nullable=False,
        default=CompletionStatus["PROGRESSING"].value
    )
    overall_score = Column(Float)
    jlpt_level = Column(Enum(LanguageLevel))
    pronounciation_score = Column(Float)
    grammar_score = Column(Float)
    flow_score = Column(Float)
    report_pdf_path = Column(String)
    created_at = Column(DateTime)


class VoiceExchange(shared_base):
    __tablename__ = "voice_exchange"

    exchange_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id = Column(
        UUID(as_uuid=True), ForeignKey("voice_interview.interview_id")
    )
    turn_number = Column(Integer)
    manager_question_text = Column(String)
    manager_question_romaji = Column(String)
    candidate_audio_path = Column(String)
    candidate_transcript = Column(String)
    pronounciation_score = Column(Float)
    grammar_score = Column(Float)
    flow_score = Column(Float)
    manager_feedback = Column(String)
    created_at = Column(DateTime)
