from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class SavedSearch(Base):
    __tablename__ = "saved_searches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    query = Column(Text, nullable=False)
    is_regex = Column(Boolean, default=False)
    is_fuzzy = Column(Boolean, default=False)
    case_sensitive = Column(Boolean, default=False)
    whole_word = Column(Boolean, default=False)
    filters = Column(JSON, default=dict)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    is_global = Column(Boolean, default=False)
    use_count = Column(Integer, default=0)
    last_used = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="saved_searches")

class SavedFilter(Base):
    __tablename__ = "saved_filters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    filter_type = Column(String(50), nullable=False)  # severity, timestamp, environment, etc.
    config = Column(JSON, default=dict)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
