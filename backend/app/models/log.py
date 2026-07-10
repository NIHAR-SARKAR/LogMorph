import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, BigInteger, JSON, Index
from sqlalchemy.orm import relationship
from app.database import Base

class Severity(str, enum.Enum):
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"
    UNKNOWN = "unknown"

class LogFile(Base):
    __tablename__ = "log_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    path = Column(String(1000), nullable=False)
    size_bytes = Column(BigInteger, default=0)
    line_count = Column(Integer, default=0)
    hash = Column(String(64), nullable=True)  # SHA256
    log_source_id = Column(Integer, ForeignKey("log_sources.id"), nullable=False)
    parser_template_id = Column(Integer, ForeignKey("parser_templates.id"), nullable=True)
    encoding = Column(String(50), default="utf-8")
    is_archived = Column(Boolean, default=False)
    is_compressed = Column(Boolean, default=False)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, nullable=True)
    last_parsed = Column(DateTime, nullable=True)
    parse_status = Column(String(50), default="pending")  # pending, parsing, completed, error
    error_message = Column(Text, nullable=True)

    log_source = relationship("LogSource", back_populates="log_files")
    entries = relationship("LogEntry", back_populates="log_file", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_logfile_source', 'log_source_id'),
        Index('idx_logfile_modified', 'last_modified'),
    )

class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    log_file_id = Column(Integer, ForeignKey("log_files.id"), nullable=False)
    line_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, nullable=True, index=True)
    severity = Column(Enum(Severity), default=Severity.UNKNOWN, index=True)
    message = Column(Text, nullable=False)
    raw_line = Column(Text, nullable=False)

    # Structured fields
    logger = Column(String(200), nullable=True, index=True)
    module = Column(String(200), nullable=True)
    class_name = Column(String(200), nullable=True)
    method = Column(String(200), nullable=True)
    thread_name = Column(String(100), nullable=True)
    thread_id = Column(String(50), nullable=True)
    process_id = Column(String(50), nullable=True)
    request_id = Column(String(255), nullable=True, index=True)
    correlation_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=True)
    machine_name = Column(String(200), nullable=True)
    exception_type = Column(String(500), nullable=True, index=True)
    exception_message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)

    # Extra fields
    custom_fields = Column(JSON, default=dict)

    # Metadata
    parsed_at = Column(DateTime, default=datetime.utcnow)
    ai_summary = Column(Text, nullable=True)
    ai_analyzed = Column(Boolean, default=False)
    bookmarked = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)

    log_file = relationship("LogFile", back_populates="entries")
    tags = relationship("LogTag", back_populates="log_entry", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_entry_timestamp', 'timestamp'),
        Index('idx_entry_severity', 'severity'),
        Index('idx_entry_request', 'request_id'),
        Index('idx_entry_correlation', 'correlation_id'),
        Index('idx_entry_exception', 'exception_type'),
        Index('idx_entry_composite', 'log_file_id', 'timestamp', 'severity'),
    )

class LogTag(Base):
    __tablename__ = "log_tags"

    id = Column(Integer, primary_key=True, index=True)
    log_entry_id = Column(Integer, ForeignKey("log_entries.id"), nullable=False)
    tag = Column(String(100), nullable=False, index=True)
    color = Column(String(7), default="#3b82f6")
    created_at = Column(DateTime, default=datetime.utcnow)

    log_entry = relationship("LogEntry", back_populates="tags")
