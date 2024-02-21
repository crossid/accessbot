from typing import Any, Optional

from pydantic import BaseModel, Field

from app.id import generate


class User(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class CurrentUser(User):
    org_id: Optional[str] = ""

    def from_userinfo(data):
        self = CurrentUser(
            id=data["sub"],
            email=data["email"],
            full_name=data["name"],
            disabled=data.get("blocked", False),
            org_id=data.get("org_id") or data.get("ext", {}).get("org_id"),
        )

        return self


class Org(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    external_id: Optional[str] = None
    display_name: str
    creator_id: str
    config: dict[str, Any] = Field(description="Organization configuration")
