from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DISABLED = "disabled"

class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    QA = "qa"
    UAT = "uat"
    STAGING = "staging"
    PRODUCTION = "production"
    CUSTOM = "custom"

class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    tags: List[str] = []
    status: ProjectStatus = ProjectStatus.ACTIVE

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[ProjectStatus] = None

class Project(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    last_scan: Optional[datetime] = None
    environment_count: int = 0
    log_source_count: int = 0

    class Config:
        from_attributes = True

class EnvironmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: EnvironmentType = EnvironmentType.DEVELOPMENT
    description: Optional[str] = None

class EnvironmentCreate(EnvironmentBase):
    project_id: int

class Environment(EnvironmentBase):
    id: int
    project_id: int
    created_at: datetime
    log_source_count: int = 0

    class Config:
        from_attributes = True

class LogSourceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    path: str = Field(..., min_length=1, max_length=1000)
    enabled: bool = True
    recursive_scan: bool = True
    auto_refresh: bool = True
    encoding: str = "utf-8"
    timezone: str = "UTC"
    retention_days: int = 90
    file_pattern: str = "*"
    parser_template_id: Optional[int] = None

class LogSourceCreate(LogSourceBase):
    project_id: int
    environment_id: int

class LogSourceUpdate(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    enabled: Optional[bool] = None
    recursive_scan: Optional[bool] = None
    auto_refresh: Optional[bool] = None
    encoding: Optional[str] = None
    timezone: Optional[str] = None
    retention_days: Optional[int] = None
    file_pattern: Optional[str] = None
    parser_template_id: Optional[int] = None

class LogSource(LogSourceBase):
    id: int
    project_id: int
    environment_id: int
    created_at: datetime
    updated_at: datetime
    last_scan: Optional[datetime] = None
    total_files: int = 0
    total_entries: int = 0
    environment: Optional[Environment] = None

    class Config:
        from_attributes = True
