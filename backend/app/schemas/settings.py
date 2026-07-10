from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class AppSettingBase(BaseModel):
    key: str = Field(..., min_length=1, max_length=200)
    value: Optional[str] = None
    value_type: str = "string"
    category: str = "general"
    description: Optional[str] = None

class AppSettingCreate(AppSettingBase):
    pass

class AppSettingUpdate(BaseModel):
    value: Optional[str] = None
    value_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None

class AppSetting(AppSettingBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True
