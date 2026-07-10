import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class ProjectStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DISABLED = "disabled"

class EnvironmentType(str, enum.Enum):
    DEVELOPMENT = "development"
    QA = "qa"
    UAT = "uat"
    STAGING = "staging"
    PRODUCTION = "production"
    CUSTOM = "custom"

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    tags = Column(JSON, default=list)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scan = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="projects")
    environments = relationship("Environment", back_populates="project", cascade="all, delete-orphan")
    log_sources = relationship("LogSource", back_populates="project", cascade="all, delete-orphan")

class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(Enum(EnvironmentType), default=EnvironmentType.DEVELOPMENT)
    description = Column(Text, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="environments")
    log_sources = relationship("LogSource", back_populates="environment")

class LogSource(Base):
    __tablename__ = "log_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    path = Column(String(1000), nullable=False)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    enabled = Column(Boolean, default=True)
    recursive_scan = Column(Boolean, default=True)
    auto_refresh = Column(Boolean, default=True)
    encoding = Column(String(50), default="utf-8")
    timezone = Column(String(100), default="UTC")
    retention_days = Column(Integer, default=90)
    parser_template_id = Column(Integer, ForeignKey("parser_templates.id"), nullable=True)
    file_pattern = Column(String(255), default="*")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scan = Column(DateTime, nullable=True)
    total_files = Column(Integer, default=0)
    total_entries = Column(Integer, default=0)

    project = relationship("Project", back_populates="log_sources")
    environment = relationship("Environment", back_populates="log_sources")
    parser_template = relationship("ParserTemplate")
    log_files = relationship("LogFile", back_populates="log_source", cascade="all, delete-orphan")
