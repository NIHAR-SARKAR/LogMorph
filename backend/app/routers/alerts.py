from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.alert import AlertRule, Notification
from app.models.user import User
from app.schemas.alert import AlertRule as ARSchema, AlertRuleCreate, AlertRuleUpdate, Notification as NotifSchema
from app.core.security import get_current_active_user, require_admin
from app.core.logging import logger

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("/rules", response_model=List[ARSchema])
def list_rules(
    project_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List alert rules."""
    query = db.query(AlertRule)
    if project_id:
        query = query.filter(AlertRule.project_id == project_id)
    return query.all()

@router.post("/rules", response_model=ARSchema)
def create_rule(
    rule: AlertRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create alert rule."""
    db_rule = AlertRule(**rule.model_dump(), created_by_id=current_user.id)
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    logger.info(f"Alert rule created: {db_rule.name} by {current_user.username}")
    return db_rule

@router.get("/rules/{rule_id}", response_model=ARSchema)
def get_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Get alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@router.put("/rules/{rule_id}", response_model=ARSchema)
def update_rule(
    rule_id: int,
    rule_update: AlertRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    for field, value in rule_update.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule

@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"message": f"Rule '{rule.name}' deleted"}

@router.get("/notifications", response_model=List[NotifSchema])
def list_notifications(
    is_read: bool = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List notifications."""
    query = db.query(Notification)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    if current_user.role.value != "admin":
        query = query.filter(Notification.user_id == current_user.id)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()

@router.put("/notifications/{notif_id}/read")
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db)
):
    """Mark notification as read."""
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"is_read": True}
