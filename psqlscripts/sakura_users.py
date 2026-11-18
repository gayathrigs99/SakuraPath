from enum import Enum
from database import Base
from sqlalchemy import Integer,String,Column

class SakuraUsers(Base):
    __table_name__="sakura_users"
    user_id: Column(Integer,primary_key=True)
    email: Column(String)
    password_hash: Column(String)
    name: str
    user_type: str
    language_level: LanguageLevel


class LanguageLevel(Enum):
    N5 = "N5"
    N4 = "N4"
    N3 = "N3"
    N2 = "N2"
    N1 = "N1"


