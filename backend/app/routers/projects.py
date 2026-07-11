from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.project import Project, Environment, LogSource
from app.models.user import User
from app.schemas.project import (
    Project as ProjectSchema, ProjectCreate, ProjectUpdate,
    Environment as EnvSchema, EnvironmentCreate,
    LogSource as LogSourceSchema, LogSourceCreate, LogSourceUpdate
)
from app.core.security import get_current_active_user, require_admin, require_developer
from app.core.logging import logger

router = APIRouter(prefix="/projects", tags=["Projects"])

# === PROJECTS ===

@router.get("", response_model=List[ProjectSchema])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all projects."""
    query = db.query(Project)

    projects = query.offset(skip).limit(limit).all()

    # Enrich with counts
    for p in projects:
        p.environment_count = db.query(Environment).filter(Environment.project_id == p.id).count()
        p.log_source_count = db.query(LogSource).filter(LogSource.project_id == p.id).count()

    return projects

@router.post("", response_model=ProjectSchema, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new project."""
    db_project = Project(
        name=project.name,
        description=project.description,
        tags=project.tags,
        status=project.status,
        owner_id=current_user.id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    logger.info(f"Project created: {db_project.name} by {current_user.username}")
    return db_project

@router.get("/{project_id}", response_model=ProjectSchema)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.environment_count = db.query(Environment).filter(Environment.project_id == project.id).count()
    project.log_source_count = db.query(LogSource).filter(LogSource.project_id == project.id).count()
    return project

@router.put("/{project_id}", response_model=ProjectSchema)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    for field, value in project_update.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete project (admin only)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    logger.info(f"Project deleted: {project.name} by {current_user.username}")
    return {"message": f"Project '{project.name}' deleted"}

# === ENVIRONMENTS ===

@router.get("/{project_id}/environments", response_model=List[EnvSchema])
def list_environments(
    project_id: int,
    db: Session = Depends(get_db)
):
    """List environments for a project."""
    envs = db.query(Environment).filter(Environment.project_id == project_id).all()
    for e in envs:
        e.log_source_count = db.query(LogSource).filter(LogSource.environment_id == e.id).count()
    return envs

@router.post("/{project_id}/environments", response_model=EnvSchema)
def create_environment(
    project_id: int,
    env: EnvironmentCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create environment for project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_env = Environment(
        name=env.name,
        type=env.type,
        description=env.description,
        project_id=project_id
    )
    db.add(db_env)
    db.commit()
    db.refresh(db_env)
    return db_env

@router.delete("/{project_id}/environments/{env_id}")
def delete_environment(
    project_id: int,
    env_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete environment."""
    env = db.query(Environment).filter(
        Environment.id == env_id,
        Environment.project_id == project_id
    ).first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")

    db.delete(env)
    db.commit()
    return {"message": f"Environment '{env.name}' deleted"}

# === LOG SOURCES ===

@router.get("/{project_id}/log-sources", response_model=List[LogSourceSchema])
def list_log_sources(
    project_id: int,
    db: Session = Depends(get_db)
):
    """List log sources for project."""
    sources = db.query(LogSource).filter(LogSource.project_id == project_id).all()
    return sources

@router.post("/{project_id}/log-sources", response_model=LogSourceSchema)
def create_log_source(
    project_id: int,
    source: LogSourceCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create log source."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    env = db.query(Environment).filter(
        Environment.id == source.environment_id,
        Environment.project_id == project_id
    ).first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found in project")

    db_source = LogSource(
        name=source.name,
        path=source.path,
        project_id=project_id,
        environment_id=source.environment_id,
        enabled=source.enabled,
        recursive_scan=source.recursive_scan,
        auto_refresh=source.auto_refresh,
        encoding=source.encoding,
        timezone=source.timezone,
        retention_days=source.retention_days,
        file_pattern=source.file_pattern,
        parser_template_id=source.parser_template_id
    )
    db.add(db_source)
    db.commit()
    db.refresh(db_source)
    return db_source

@router.get("/{project_id}/log-sources/{source_id}", response_model=LogSourceSchema)
def get_log_source(
    project_id: int,
    source_id: int,
    db: Session = Depends(get_db)
):
    """Get log source."""
    source = db.query(LogSource).filter(
        LogSource.id == source_id,
        LogSource.project_id == project_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Log source not found")
    return source

@router.put("/{project_id}/log-sources/{source_id}", response_model=LogSourceSchema)
def update_log_source(
    project_id: int,
    source_id: int,
    source_update: LogSourceUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update log source."""
    source = db.query(LogSource).filter(
        LogSource.id == source_id,
        LogSource.project_id == project_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Log source not found")

    for field, value in source_update.model_dump(exclude_unset=True).items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)
    return source

@router.delete("/{project_id}/log-sources/{source_id}")
def delete_log_source(
    project_id: int,
    source_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete log source."""
    source = db.query(LogSource).filter(
        LogSource.id == source_id,
        LogSource.project_id == project_id
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Log source not found")

    db.delete(source)
    db.commit()
    return {"message": f"Log source '{source.name}' deleted"}
