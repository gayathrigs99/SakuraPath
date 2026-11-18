from enum import Enum


class LanguageLevel(Enum):
    N5 = "N5"
    N4 = "N4"
    N3 = "N3"
    N2 = "N2"
    N1 = "N1"


class CompletionStatus(str, Enum):
    COMPLETE = "completed"
    ABANDONED   = "abandoned"
    PROGRESSING = "progressing"


class ReadinessLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    READY = "job_ready"


class UserType(Enum):
    LEARNER = "learner"
    ADMIN = "admin"
    EMPLOYER = "employer"


class UserStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
