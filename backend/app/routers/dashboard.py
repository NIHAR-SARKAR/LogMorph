from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.project import Project, LogSource
from app.models.log import LogFile, LogEntry, Severity
from app.models.analysis import ActivityLog
from app.models.alert import Notification
from app.schemas.analysis import DashboardStats, ActivityLog as ActivityLogSchema
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get aggregated dashboard statistics."""
    total_projects = db.query(Project).count()
    total_log_files = db.query(LogFile).count()
    total_entries = db.query(LogEntry).count()
    active_monitors = db.query(LogSource).filter(LogSource.enabled == True).count()

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    logs_today = db.query(LogEntry).filter(LogEntry.timestamp >= today_start).count()
    errors_today = (
        db.query(LogEntry)
        .filter(LogEntry.timestamp >= today_start, LogEntry.severity == Severity.ERROR)
        .count()
    )
    warnings_today = (
        db.query(LogEntry)
        .filter(LogEntry.timestamp >= today_start, LogEntry.severity == Severity.WARNING)
        .count()
    )
    critical_logs = db.query(LogEntry).filter(LogEntry.severity == Severity.CRITICAL).count()
    ai_alerts = db.query(Notification).count()

    total_size = db.query(func.sum(LogFile.size_bytes)).scalar() or 0
    storage_used_mb = round(total_size / (1024 * 1024), 2)

    recent_activities = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(10)
        .all()
    )

    top_error_categories = (
        db.query(
            LogEntry.exception_type,
            func.count(LogEntry.id).label("count")
        )
        .filter(LogEntry.exception_type != None)
        .group_by(LogEntry.exception_type)
        .order_by(func.count(LogEntry.id).desc())
        .limit(5)
        .all()
    )

    severity_counts = {}
    for sev in Severity:
        severity_counts[sev.value] = db.query(LogEntry).filter(LogEntry.severity == sev).count()

    return DashboardStats(
        total_projects=total_projects,
        total_log_files=total_log_files,
        total_entries=total_entries,
        active_monitors=active_monitors,
        logs_today=logs_today,
        errors_today=errors_today,
        warnings_today=warnings_today,
        critical_logs=critical_logs,
        ai_alerts=ai_alerts,
        storage_used_mb=storage_used_mb,
        recent_activities=[ActivityLogSchema.model_validate(a) for a in recent_activities],
        recent_searches=[],
        top_error_categories=[
            {"exception_type": exc, "count": cnt}
            for exc, cnt in top_error_categories
        ],
        top_applications=[],
        environment_health=[],
        log_volume_data=_log_volume_data(db),
        error_trend_data=_error_trend_data(db),
    )


@router.get("/log-volume")
def get_log_volume(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get log volume over time."""
    return {"data": _log_volume_data(db, days)}


@router.get("/severity-chart")
def get_severity_chart(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get severity distribution over time for charts."""
    return {"data": _error_trend_data(db, days)}


def _log_volume_data(db: Session, days: int = 7) -> List[Dict[str, Any]]:
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    results = (
        db.query(
            func.date(LogEntry.timestamp).label("date"),
            func.count(LogEntry.id).label("count")
        )
        .filter(LogEntry.timestamp >= from_date)
        .group_by(func.date(LogEntry.timestamp))
        .order_by(func.date(LogEntry.timestamp))
        .all()
    )
    return [{"date": str(date), "count": count} for date, count in results]


def _error_trend_data(db: Session, days: int = 7) -> List[Dict[str, Any]]:
    from_date = datetime.now(timezone.utc) - timedelta(days=days)
    results = (
        db.query(
            func.date(LogEntry.timestamp).label("date"),
            LogEntry.severity,
            func.count(LogEntry.id).label("count")
        )
        .filter(LogEntry.timestamp >= from_date)
        .group_by(func.date(LogEntry.timestamp), LogEntry.severity)
        .order_by(func.date(LogEntry.timestamp))
        .all()
    )

    data_by_date: Dict[str, Dict[str, Any]] = {}
    for date, severity, count in results:
        date_str = str(date)
        if date_str not in data_by_date:
            data_by_date[date_str] = {"date": date_str}
        data_by_date[date_str][severity.value] = count

    return list(data_by_date.values())
