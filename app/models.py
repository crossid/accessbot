import enum
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from .id import generate


class User(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class CurrentUser(User):
    org_id: Optional[str] = None

    def from_oauth2(userinfo, decoded_access_token: dict[str, Any]):
        self = CurrentUser(
            id=decoded_access_token["sub"],
            email=userinfo["email"],
            full_name=userinfo["name"],
            disabled=userinfo.get("blocked", False),
            org_id=decoded_access_token.get("org_id")
            or decoded_access_token.get("ext", {}).get("org_id")
            or None,
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
    Enum class representing the status of a request

    - active: an active conversation between the requester and the LLM.
    - submitted: the request has been submitted and is pending approval.
    - approval: pending data owner approval.
    - completed: the request has been completed, whether it was approved or denied.
    """

    active = "active"
    submitted = "submitted"
    approval = "approval"
    completed = "completed"


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    conversation_id: str = Field(default=None)
    org_id: Optional[str] = Field(default=None)
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
        default=None, description="Messages related to the request"
    )
