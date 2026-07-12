from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
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
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get aggregated dashboard statistics.

    days=0 means all time. Default 7 days.
    """
    # Global counts (not time-scoped)
    total_projects = db.query(Project).count()
    total_log_files = db.query(LogFile).count()
    active_monitors = db.query(LogSource).filter(LogSource.enabled == True).count()
    ai_alerts = db.query(Notification).count()

    total_size = db.query(func.sum(LogFile.size_bytes)).scalar() or 0
    storage_used_mb = round(total_size / (1024 * 1024), 2)

    # Build the time-scoped base filter
    now = datetime.now(timezone.utc)
    if days > 0:
        from_date = now - timedelta(days=days)
        time_filter = LogEntry.timestamp >= from_date
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        time_filter = None  # all time

    # Single query for total entries + error + warning + critical counts in the time range
    if time_filter is not None:
        agg = db.query(
            func.count(LogEntry.id).label("total"),
            func.sum(case((LogEntry.severity == Severity.ERROR, 1), else_=0)).label("errors"),
            func.sum(case((LogEntry.severity == Severity.WARNING, 1), else_=0)).label("warnings"),
            func.sum(case((LogEntry.severity == Severity.CRITICAL, 1), else_=0)).label("critical"),
        ).filter(time_filter).one()
        total_entries = agg.total or 0
        errors_in_range = agg.errors or 0
        warnings_in_range = agg.warnings or 0
        critical_in_range = agg.critical or 0

        # "Today" stats (always relative to today regardless of days filter)
        today_agg = db.query(
            func.count(LogEntry.id).label("total"),
            func.sum(case((LogEntry.severity == Severity.ERROR, 1), else_=0)).label("errors"),
            func.sum(case((LogEntry.severity == Severity.WARNING, 1), else_=0)).label("warnings"),
        ).filter(LogEntry.timestamp >= today_start).one()
        logs_today = today_agg.total or 0
        errors_today = today_agg.errors or 0
        warnings_today = today_agg.warnings or 0
    else:
        # All time — single aggregate query
        agg = db.query(
            func.count(LogEntry.id).label("total"),
            func.sum(case((LogEntry.severity == Severity.ERROR, 1), else_=0)).label("errors"),
            func.sum(case((LogEntry.severity == Severity.WARNING, 1), else_=0)).label("warnings"),
            func.sum(case((LogEntry.severity == Severity.CRITICAL, 1), else_=0)).label("critical"),
        ).one()
        total_entries = agg.total or 0
        errors_today = agg.errors or 0
        warnings_today = agg.warnings or 0
        critical_in_range = agg.critical or 0
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_agg = db.query(
            func.count(LogEntry.id).label("total"),
            func.sum(case((LogEntry.severity == Severity.ERROR, 1), else_=0)).label("errors"),
            func.sum(case((LogEntry.severity == Severity.WARNING, 1), else_=0)).label("warnings"),
        ).filter(LogEntry.timestamp >= today_start).one()
        logs_today = today_agg.total or 0
        errors_today = today_agg.errors or 0
        warnings_today = today_agg.warnings or 0

    # Recent activities (not time-scoped, just latest 10)
    recent_activities = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
        .limit(10)
        .all()
    )

    # Top error categories — single group_by query with time filter
    error_q = (
        db.query(
            LogEntry.exception_type,
            func.count(LogEntry.id).label("count")
        )
        .filter(LogEntry.exception_type != None)
    )
    if time_filter is not None:
        error_q = error_q.filter(time_filter)
    top_error_categories = error_q.group_by(LogEntry.exception_type).order_by(func.count(LogEntry.id).desc()).limit(5).all()

    return DashboardStats(
        total_projects=total_projects,
        total_log_files=total_log_files,
        total_entries=total_entries,
        active_monitors=active_monitors,
        logs_today=logs_today,
        errors_today=errors_today,
        warnings_today=warnings_today,
        critical_logs=critical_in_range,
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
        log_volume_data=_log_volume_data(db, days),
        error_trend_data=_error_trend_data(db, days),
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
    q = db.query(
        func.date(LogEntry.timestamp).label("date"),
        func.count(LogEntry.id).label("count")
    )
    if days > 0:
        from_date = datetime.now(timezone.utc) - timedelta(days=days)
        q = q.filter(LogEntry.timestamp >= from_date)
    results = q.group_by(func.date(LogEntry.timestamp)).order_by(func.date(LogEntry.timestamp)).all()
    return [{"date": str(date), "count": count} for date, count in results]


def _error_trend_data(db: Session, days: int = 7) -> List[Dict[str, Any]]:
    q = db.query(
        func.date(LogEntry.timestamp).label("date"),
        LogEntry.severity,
        func.count(LogEntry.id).label("count")
    )
    if days > 0:
        from_date = datetime.now(timezone.utc) - timedelta(days=days)
        q = q.filter(LogEntry.timestamp >= from_date)
    results = q.group_by(func.date(LogEntry.timestamp), LogEntry.severity).order_by(func.date(LogEntry.timestamp)).all()

    data_by_date: Dict[str, Dict[str, Any]] = {}
    for date, severity, count in results:
        date_str = str(date)
        if date_str not in data_by_date:
            data_by_date[date_str] = {"date": date_str}
        data_by_date[date_str][severity.value] = count

    return list(data_by_date.values())
