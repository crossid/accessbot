import enum
from datetime import datetime
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
    # TODO rename to created_by
    creator_id: str
    config: dict[str, Any] = Field(description="Organization configuration")


class StatusEnum(enum.Enum):
    """
    Enum class representing the status of a resource

    - active: In conversation.
    - approval: The object is pending approval.
    - submitted: ???????????
    - completed: The object has been completed.
    """

    active = "active"
    submitted = "submitted"
    approval = "approval"
    completed = "completed"


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    conversation_id: str = Field(default=None)
    type: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    # TODO created_by


class AccessRequest(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    status: StatusEnum = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.now)
    external_id: Optional[str] = Field(default=None)
    context: dict[str, Any] = Field(description="context of the request")
    owner_id: str
    org_id: Optional[str]
    messages: Optional[list[ChatMessage]] = Field(
        default=[], description="Messages related to the request"
    )
