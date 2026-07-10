from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User as UserModel, UserRole
from app.schemas.user import UserCreate, User, Token, PasswordReset
from app.core.security import (
    verify_password, get_password_hash, create_access_token, 
    create_refresh_token, get_current_active_user, require_admin
)
from app.core.logging import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user. Only admins can create users in production."""
    # Check if user exists
    existing = db.query(UserModel).filter(
        (UserModel.username == user_data.username) | (UserModel.email == user_data.email)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username or email already registered")

    # Create first user as admin
    user_count = db.query(UserModel).count()
    role = UserRole.ADMIN if user_count == 0 else user_data.role

    user = UserModel(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=role,
        is_active=True,
        is_superuser=(user_count == 0)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"User registered: {user.username} (role: {user.role})")
    return user

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and get access token."""
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is disabled")

    user.last_login = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    logger.info(f"User logged in: {user.username}")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=60 * 24,
        user=user
    )

@router.post("/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token."""
    from app.core.security import decode_token
    payload = decode_token(refresh_token)
    if not payload or payload.type != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(UserModel).filter(UserModel.id == payload.sub, UserModel.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return current_user

@router.put("/me")
def update_me(
    user_update: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile."""
    if "email" in user_update:
        current_user.email = user_update["email"]
    if "full_name" in user_update:
        current_user.full_name = user_update["full_name"]
    if "password" in user_update and user_update["password"]:
        current_user.hashed_password = get_password_hash(user_update["password"])

    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/reset-password")
def reset_password(
    data: PasswordReset,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin can reset any user's password."""
    user = db.query(UserModel).filter(UserModel.id == data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    logger.info(f"Password reset for user {user.username} by admin {admin.username}")
    return {"message": "Password reset successfully"}

@router.get("/users", response_model=list[User])
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all users (admin only)."""
    return db.query(UserModel).offset(skip).limit(limit).all()

@router.put("/users/{user_id}/disable")
def disable_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Disable a user account (admin only)."""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Cannot disable superuser")

    user.is_active = False
    db.commit()
    logger.info(f"User {user.username} disabled by {admin.username}")
    return {"message": f"User {user.username} disabled"}

@router.put("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    role: UserRole,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user role (admin only)."""
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_superuser:
        raise HTTPException(status_code=400, detail="Cannot change superuser role")

    user.role = role
    db.commit()
    return {"message": f"User {user.username} role updated to {role}"}
