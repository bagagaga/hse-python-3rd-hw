from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
from .utils import default_expires_at


class LinkRead(BaseModel):
    id: UUID
    short_code: str
    original_url: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    visit_count: int
    expires_at: datetime

    class Config:
        from_attributes = True


class LinkCreate(BaseModel):
    original_url: str
    custom_alias: str = Field(None, max_length=100)
    expires_at: Optional[datetime] = Field(default_factory=default_expires_at)


class LinkUpdate(BaseModel):
    original_url: Optional[str] = None
    expires_at: Optional[datetime] = None
