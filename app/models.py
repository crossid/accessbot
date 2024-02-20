from typing import Any, Optional

from pydantic import BaseModel, Field

from app.id import generate


class User(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class Org(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    external_id: Optional[str] = None
    display_name: str
    creator_id: str
    config: dict[str, Any] = Field(description="Organization configuration")
