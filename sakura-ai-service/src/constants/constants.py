from enum import Enum

SUCCESS = "success"
FAILED = "failed"


class SakuraConstants(str, Enum):
    ERROR = "error"
    INFO = "info"
    WARNING = "warning"
    DEBUG = "debug"
    CRITICAL = "critical"


