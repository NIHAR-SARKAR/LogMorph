from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class Severity(str, Enum):
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

class LogFileBase(BaseModel):
    filename: str
    path: str
    size_bytes: int = 0
    line_count: int = 0
    encoding: str = "utf-8"
    is_archived: bool = False
    is_compressed: bool = False

class LogFileCreate(LogFileBase):
    log_source_id: int

class LogFile(LogFileBase):
    id: int
    log_source_id: int
    hash: Optional[str] = None
    first_seen: datetime
    last_modified: Optional[datetime] = None
    last_parsed: Optional[datetime] = None
    parse_status: str = "pending"
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class LogEntryBase(BaseModel):
    line_number: int
    timestamp: Optional[datetime] = None
    severity: Severity = Severity.UNKNOWN
    message: str
    raw_line: str

class LogEntryCreate(LogEntryBase):
    log_file_id: int
    logger: Optional[str] = None
    module: Optional[str] = None
    class_name: Optional[str] = None
    method: Optional[str] = None
    thread_name: Optional[str] = None
    thread_id: Optional[str] = None
    process_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    machine_name: Optional[str] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    custom_fields: Dict[str, Any] = {}

class LogEntry(LogEntryBase):
    id: int
    log_file_id: int
    logger: Optional[str] = None
    module: Optional[str] = None
    class_name: Optional[str] = None
    method: Optional[str] = None
    thread_name: Optional[str] = None
    thread_id: Optional[str] = None
    process_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    machine_name: Optional[str] = None
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    stack_trace: Optional[str] = None
    custom_fields: Dict[str, Any] = {}
    parsed_at: datetime
    ai_summary: Optional[str] = None
    ai_analyzed: bool = False
    bookmarked: bool = False
    notes: Optional[str] = None
    tags: List[str] = []

    class Config:
        from_attributes = True

class LogEntryFilter(BaseModel):
    project_id: Optional[int] = None
    environment_id: Optional[int] = None
    log_source_id: Optional[int] = None
    log_file_id: Optional[int] = None
    severity: Optional[List[Severity]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search_query: Optional[str] = None
    is_regex: bool = False
    exception_type: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    logger: Optional[str] = None
    module: Optional[str] = None
    machine_name: Optional[str] = None
    custom_filters: Optional[Dict[str, Any]] = None
    bookmarked_only: bool = False
    limit: int = 1000
    offset: int = 0

class LogStats(BaseModel):
    total_entries: int
    error_count: int
    warning_count: int
    critical_count: int
    fatal_count: int
    info_count: int
    debug_count: int
    trace_count: int
    unique_exceptions: int
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
