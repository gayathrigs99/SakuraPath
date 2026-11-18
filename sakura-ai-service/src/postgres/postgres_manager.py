import inspect
import os
import time
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from src.logger.logger import SakuraLogger
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

load_dotenv()

db_name = os.getenv("PG_DBNAME")
db_pswd = os.getenv("PG_PASSWORD")
db_host = os.getenv("PG_HOST")
db_port = os.getenv("PG_PORT")
db_user = os.getenv("PG_USER")

logger = SakuraLogger()


class PostgresManager:
    """Singleton Database Connection Manager"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            self.db_engine = create_engine(
                f"postgresql://{db_user}:{db_pswd}@{db_host}:{db_port}/{db_name}",
                pool_size=5,
                pool_recycle=3600,
                pool_pre_ping=True,
            )
            self.session_local = sessionmaker(bind=self.db_engine)
            self._initialized = True
            logger.info_log(f"Database connected: {db_host}:{db_port}/{db_name}")
        except Exception as e:
            logger.critical_log(f"Database connection failed: {e}")
            raise

    @classmethod
    def get_instance(cls) -> "PostgresManager":
        return cls()

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.session_local()

    @contextmanager
    def session_scope(self):
        """Context manager for safe session usage"""
        session = self.session_local()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error_log(f"Session rollback triggered: {e}")
            raise
        finally:
            session.close()
