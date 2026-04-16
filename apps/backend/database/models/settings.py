from sqlalchemy import Column, String, JSON
from apps.backend.database.base import Base

class Settings(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
