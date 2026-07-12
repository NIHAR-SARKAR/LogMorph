from datetime import datetime, timedelta, timezone
from typing import Optional, Union
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.config import get_settings
from app.schemas.user import TokenPayload

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    ).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # python-jose requires the subject claim to be a string
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[TokenPayload]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_raw = payload.get("sub")
        token_type: str = payload.get("type", "access")
        if user_id_raw is None:
            return None
        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            return None
        return TokenPayload(sub=user_id, exp=payload.get("exp"), type=token_type)
    except JWTError:
        return None

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None or payload.sub is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == payload.sub, User.is_active == True).first()
    if user is None:
        raise credentials_exception

    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_developer(current_user: User = Depends(get_current_active_user)) -> User:
    from app.models.user import UserRole
    if current_user.role not in [UserRole.ADMIN, UserRole.DEVELOPER] and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Developer access required"
        )
    return current_user


def get_user_accessible_project_ids(user: User, db: Session) -> set[int]:
    """Return set of project IDs the user is allowed to access.

    Admin / superuser can access everything.
    Other roles need explicit project mapping via user_project_access.
    """
    from app.models.user import UserRole
    if user.role == UserRole.ADMIN or user.is_superuser:
        from app.models.project import Project
        return {p.id for p in db.query(Project.id).all()}
    explicit = {p.id for p in user.accessible_projects}
    owned = {p.id for p in user.projects}
    return explicit | owned


def check_project_access(user: User, project_id: int, db: Session) -> bool:
    """Return True if user can access the given project."""
    from app.models.user import UserRole
    if user.role == UserRole.ADMIN or user.is_superuser:
        return True
    # Check owned projects
    if any(p.id == project_id for p in user.projects):
        return True
    # Check explicit access
    return any(p.id == project_id for p in user.accessible_projects)
