import inspect
import os
import threading
from datetime import datetime
from src.constants.constants import SakuraConstants

_LEVEL_ORDER = {
    SakuraConstants.INFO: 0,
    SakuraConstants.WARNING: 1,
    SakuraConstants.ERROR: 2,
    SakuraConstants.DEBUG: 3,
    SakuraConstants.CRITICAL: 4,
}


class SakuraLogger:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args,**kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._logs = []
                    cls._instance._log_level = SakuraConstants.INFO
        return cls._instance

    def set_level(self, level: SakuraConstants):
        self._log_level = level

    def _get_caller_location(self):
        # Walk past this frame and the info_log/warning_log/etc wrapper
        # frame to find the actual call site.
        frame = inspect.currentframe()
        try:
            caller = frame.f_back.f_back.f_back
            filename = os.path.basename(caller.f_code.co_filename)
            return f"{filename}:{caller.f_lineno}"
        except AttributeError:
            return "unknown:0"
        finally:
            del frame

    def _write_log(self, level: SakuraConstants, message: str):
        if _LEVEL_ORDER.get(level, 0) < _LEVEL_ORDER.get(self._log_level, 0):
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        location = self._get_caller_location()
        entry = f"[{timestamp}] [{level.value.upper()}] [{location}] {message}"
        self._logs.append(entry)
        print(entry)
        return entry

    def info_log(self, message: str):
        self._write_log(SakuraConstants.INFO, message)

    def warning_log(self, message: str):
        self._write_log(SakuraConstants.WARNING, message)

    def error_log(self, message: str):
        self._write_log(SakuraConstants.ERROR, message)

    def debug_log(self, message: str):
        self._write_log(SakuraConstants.DEBUG, message)

    def critical_log(self, message: str):
        self._write_log(SakuraConstants.CRITICAL, message)

    def get_logs(self):
        return self._logs.copy()
