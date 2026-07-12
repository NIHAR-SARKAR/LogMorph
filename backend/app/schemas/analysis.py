from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class ReportType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"
    INCIDENT = "incident"
    EXECUTIVE = "executive"

class AnalysisReportBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    report_type: ReportType = ReportType.CUSTOM
    project_id: Optional[int] = None
    environment_id: Optional[int] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None

class AnalysisReportCreate(AnalysisReportBase):
    pass

class AnalysisReport(AnalysisReportBase):
    id: int
    summary: Optional[str] = None
    findings: List[Dict[str, Any]] = []
    charts: List[Dict[str, Any]] = []
    ai_insights: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ActivityLog(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class DashboardStats(BaseModel):
    total_projects: int
    total_log_files: int
    total_entries: int
    active_monitors: int
    logs_today: int
    errors_today: int
    warnings_today: int
    errors_in_range: int = 0
    warnings_in_range: int = 0
    critical_logs: int
    ai_alerts: int
    storage_used_mb: float
    recent_activities: List[ActivityLog] = []
    recent_searches: List[Dict[str, Any]] = []
    top_error_categories: List[Dict[str, Any]] = []
    top_applications: List[Dict[str, Any]] = []
    environment_health: List[Dict[str, Any]] = []
    log_volume_data: List[Dict[str, Any]] = []
    error_trend_data: List[Dict[str, Any]] = []
