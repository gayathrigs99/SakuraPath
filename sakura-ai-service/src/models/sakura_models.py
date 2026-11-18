import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    Date,
    Integer,
    JSON,
    Boolean,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from src.models.shared_base import shared_base
from src.enums.level_and_comp_status import LanguageLevel, UserType, UserStatus


class SakuraUsers(shared_base):
    __tablename__ = "sakura_users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    name = Column(String)
    user_type = Column(Enum(UserType))
    language_level = Column(Enum(LanguageLevel))
    cohort_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime)
    last_login = Column(DateTime)
    status = Column(Enum(UserStatus))


class SakuraCohorts(shared_base):
    __tablename__ = "sakura_cohorts"

    cohort_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("sakura_users.user_id"))
    start_date = Column(DateTime)
    expected_end_date = Column(Date)
    targeted_job_readiness_score = Column(Integer)
    created_at = Column(DateTime)


class SakuraScenarios(shared_base):
    __tablename__ = "sakura_scenarios"

    scenario_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String)
    description = Column(String)
    level = Column(Enum(LanguageLevel, name="language_level"))
    job_domain = Column(String)
    scenario_tree = Column(JSON)
    vocabulary_list = Column(JSON)
    grammar_focus = Column(JSON)
    cultural_notes = Column(JSON)
    is_active = Column(Boolean, default=True)
