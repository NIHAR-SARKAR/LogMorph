from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ParserTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    format_type: str = Field(..., pattern="^(regex|json|csv|delimiter|custom)$")
    pattern: str
    timestamp_format: Optional[str] = None
    severity_mapping: Dict[str, str] = {}
    field_mapping: Dict[str, str] = {}
    sample_log: Optional[str] = None
    is_shared: bool = False

class ParserTemplateCreate(ParserTemplateBase):
    pass

class ParserTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    format_type: Optional[str] = None
    pattern: Optional[str] = None
    timestamp_format: Optional[str] = None
    severity_mapping: Optional[Dict[str, str]] = None
    field_mapping: Optional[Dict[str, str]] = None
    sample_log: Optional[str] = None
    is_shared: Optional[bool] = None

class ParserTemplate(ParserTemplateBase):
    id: int
    is_builtin: bool = False
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ParserTestRequest(BaseModel):
    pattern: str
    format_type: str
    sample_log: str
    timestamp_format: Optional[str] = None
    severity_mapping: Dict[str, str] = {}
    field_mapping: Dict[str, str] = {}

class ParserTestResult(BaseModel):
    success: bool
    extracted_fields: Dict[str, Any] = {}
    timestamp: Optional[datetime] = None
    severity: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
