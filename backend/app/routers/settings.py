from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.settings import AppSetting
from app.models.user import User
from app.schemas.settings import AppSetting as SettingSchema, AppSettingCreate, AppSettingUpdate
from app.core.security import get_current_active_user, require_admin

router = APIRouter(prefix="/settings", tags=["Settings"])

@router.get("", response_model=List[SettingSchema])
def list_settings(
    category: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List application settings."""
    query = db.query(AppSetting)
    if category:
        query = query.filter(AppSetting.category == category)
    return query.all()

@router.get("/{key}", response_model=SettingSchema)
def get_setting(
    key: str,
    db: Session = Depends(get_db)
):
    """Get setting by key."""
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return setting

@router.post("", response_model=SettingSchema)
def create_setting(
    setting: AppSettingCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Create setting (admin only)."""
    existing = db.query(AppSetting).filter(AppSetting.key == setting.key).first()
    if existing:
        raise HTTPException(status_code=400, detail="Setting already exists")

    db_setting = AppSetting(**setting.model_dump())
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting

@router.put("/{key}", response_model=SettingSchema)
def update_setting(
    key: str,
    setting_update: AppSettingUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Update setting (admin only)."""
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    for field, value in setting_update.model_dump(exclude_unset=True).items():
        setattr(setting, field, value)
    db.commit()
    db.refresh(setting)
    return setting

@router.delete("/{key}")
def delete_setting(
    key: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Delete setting (admin only)."""
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    db.delete(setting)
    db.commit()
    return {"message": f"Setting '{key}' deleted"}
