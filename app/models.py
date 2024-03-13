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
    workspace_id: Optional[str] = None

    def from_oauth2(self, userinfo, decoded_access_token: dict[str, Any]):
        self = CurrentUser(
            id=decoded_access_token["sub"],
            email=userinfo["email"],
            full_name=userinfo["name"],
            disabled=userinfo.get("blocked", False),
            workspace_id=decoded_access_token.get("org_id")
            or decoded_access_token.get("ext", {}).get("org_id")
            or None,
        )

        return self


class WorkspaceStatuses(enum.Enum):
    creating = "creating"
    active = "active"


class Workspace(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    external_id: Optional[str] = None
    display_name: str
    status: WorkspaceStatuses = Field(default=WorkspaceStatuses.creating)
    created_by: str
    config: dict[str, Any] = Field(description="Workspace configuration")


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    conversation_id: str = Field(default=None)
    workspace_id: Optional[str] = Field(default=None)
    type: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)
    # TODO created_by


class ConversationStatuses(enum.Enum):
    """
    Enum class representing the status of a conversation

    - active: an active conversation between the requester and the LLM.
    - submitted: the conversation has been submitted, probably pending approval.
    - completed: the conversation has been completed, whether fulfilled or denied.
    """

    active = "active"
    submitted = "submitted"
    completed = "completed"


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    workspace_id: Optional[str]
    status: ConversationStatuses = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.now)
    external_id: Optional[str] = Field(default=None)
    context: dict[str, Any] = Field(description="context of the conversation")
    created_by: str
    messages: Optional[list[ChatMessage]] = Field(
        default=None, description="Messages related to the conversations"
    )


# Payloads
#


class PaginatedListBase(BaseModel):
    total: int
