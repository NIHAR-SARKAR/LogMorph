from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

class AlertCondition(str, Enum):
    NEW_ERROR = "new_error"
    FATAL_ERROR = "fatal_error"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    PATTERN_MATCH = "pattern_match"
    DISK_ISSUE = "disk_issue"
    AUTH_FAILURE = "auth_failure"
    DB_FAILURE = "db_failure"
    CUSTOM_REGEX = "custom_regex"

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    condition: AlertCondition
    config: Dict[str, Any] = {}
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    project_id: Optional[int] = None
    environment_id: Optional[int] = None
    log_source_id: Optional[int] = None
    cooldown_minutes: int = 15
    notify_desktop: bool = True
    notify_email: bool = False
    email_recipients: List[str] = []
    notify_webhook: bool = False
    webhook_url: Optional[str] = None
    notify_slack: bool = False
    slack_webhook: Optional[str] = None
    notify_teams: bool = False
    teams_webhook: Optional[str] = None
    notify_discord: bool = False
    discord_webhook: Optional[str] = None

class AlertRuleCreate(AlertRuleBase):
    pass

class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    condition: Optional[AlertCondition] = None
    config: Optional[Dict[str, Any]] = None
    severity: Optional[AlertSeverity] = None
    enabled: Optional[bool] = None
    cooldown_minutes: Optional[int] = None
    notify_desktop: Optional[bool] = None
    notify_email: Optional[bool] = None
    email_recipients: Optional[List[str]] = None
    notify_webhook: Optional[bool] = None
    webhook_url: Optional[str] = None
    notify_slack: Optional[bool] = None
    slack_webhook: Optional[str] = None
    notify_teams: Optional[bool] = None
    teams_webhook: Optional[str] = None
    notify_discord: Optional[bool] = None
    discord_webhook: Optional[str] = None

class AlertRule(AlertRuleBase):
    id: int
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    created_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class Notification(BaseModel):
    id: int
    title: str
    message: str
    severity: AlertSeverity
    is_read: bool = False
    user_id: Optional[int] = None
    alert_rule_id: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
