from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.core.security import get_current_active_user

class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_active_user)):
        if user.role not in self.allowed_roles and not user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted"
            )
        return user

require_admin = RoleChecker([UserRole.ADMIN])
require_developer = RoleChecker([UserRole.ADMIN, UserRole.DEVELOPER])
require_any = RoleChecker([UserRole.ADMIN, UserRole.DEVELOPER, UserRole.VIEWER])
