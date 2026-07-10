from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class SavedSearchBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    query: str
    is_regex: bool = False
    is_fuzzy: bool = False
    case_sensitive: bool = False
    whole_word: bool = False
    filters: Dict[str, Any] = {}
    is_global: bool = False

class SavedSearchCreate(SavedSearchBase):
    project_id: Optional[int] = None

class SavedSearch(SavedSearchBase):
    id: int
    user_id: int
    project_id: Optional[int] = None
    use_count: int = 0
    last_used: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SavedFilterBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    filter_type: str
    config: Dict[str, Any] = {}
    is_pinned: bool = False

class SavedFilterCreate(SavedFilterBase):
    pass

class SavedFilter(SavedFilterBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
