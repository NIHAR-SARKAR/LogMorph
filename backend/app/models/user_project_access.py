from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime
from app.database import Base

class UserProjectAccess(Base):
    __tablename__ = "user_project_access"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), primary_key=True)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
