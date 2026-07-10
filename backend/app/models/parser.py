from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class ParserTemplate(Base):
    __tablename__ = "parser_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    format_type = Column(String(50), nullable=False)  # regex, json, csv, delimiter, custom
    pattern = Column(Text, nullable=False)
    timestamp_format = Column(String(200), nullable=True)
    severity_mapping = Column(JSON, default=dict)  # {"ERROR": "error", ...}
    field_mapping = Column(JSON, default=dict)  # {"group1": "timestamp", ...}
    sample_log = Column(Text, nullable=True)
    is_builtin = Column(Boolean, default=False)
    is_shared = Column(Boolean, default=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = relationship("User")
