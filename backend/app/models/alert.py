import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.database import Base

class AlertCondition(str, enum.Enum):
    NEW_ERROR = "new_error"
    FATAL_ERROR = "fatal_error"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    PATTERN_MATCH = "pattern_match"
    DISK_ISSUE = "disk_issue"
    AUTH_FAILURE = "auth_failure"
    DB_FAILURE = "db_failure"
    CUSTOM_REGEX = "custom_regex"

class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    condition = Column(Enum(AlertCondition), nullable=False)
    config = Column(JSON, default=dict)  # threshold, pattern, regex, etc.
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.WARNING)
    enabled = Column(Boolean, default=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=True)
    log_source_id = Column(Integer, ForeignKey("log_sources.id"), nullable=True)
    cooldown_minutes = Column(Integer, default=15)
    last_triggered = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Delivery config
    notify_desktop = Column(Boolean, default=True)
    notify_email = Column(Boolean, default=False)
    email_recipients = Column(JSON, default=list)
    notify_webhook = Column(Boolean, default=False)
    webhook_url = Column(String(500), nullable=True)
    notify_slack = Column(Boolean, default=False)
    slack_webhook = Column(String(500), nullable=True)
    notify_teams = Column(Boolean, default=False)
    teams_webhook = Column(String(500), nullable=True)
    notify_discord = Column(Boolean, default=False)
    discord_webhook = Column(String(500), nullable=True)

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(Enum(AlertSeverity), default=AlertSeverity.INFO)
    is_read = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    alert_rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=True)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
