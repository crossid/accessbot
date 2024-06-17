import enum
from datetime import datetime
from typing import Any, ClassVar, Generic, List, Optional, Set, TypeVar

from pydantic import BaseModel, Field, field_validator

from .id import generate


def must_be_lowercase_alphanumeric_validator(v: str):
    if not v.isalnum() or not v.islower():
        raise ValueError("must be lowercase alphanumeric")
    return v


class OptionalModel(BaseModel):
    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)

        for field in cls.model_fields.values():
            field.default = None
            field.default_factory = None

        cls.model_rebuild(force=True)


class User(BaseModel):
    id: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class CurrentUser(User):
    workspace_id: Optional[str] = None

    @staticmethod
    def from_oauth2(userinfo, decoded_access_token: dict[str, Any]):
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
    error = "error"


class Workspace(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    external_id: Optional[str] = None
    unique_name: str
    _normalize_unique_name = field_validator("unique_name")(
        must_be_lowercase_alphanumeric_validator
    )
    display_name: str
    logo_url: Optional[str] = None
    status: WorkspaceStatuses = Field(default=WorkspaceStatuses.creating)
    created_by: str
    config: dict[str, Any] = Field(description="Workspace configuration")
    created_at: datetime = Field(default_factory=datetime.now)


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
    - completed: the conversation has been reached it's end.
    """

    active = "active"
    completed = "completed"
    cancelled = "cancelled"
    approved = "approved"
    denied = "denied"


class ConversationTypes(enum.Enum):
    recommendation = "recommendation"
    data_owner = "dataowner"


class Conversation(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    workspace_id: str
    type: ConversationTypes = Field(default=ConversationTypes.recommendation)
    status: ConversationStatuses = Field(default="active")
    created_at: datetime = Field(default_factory=datetime.now)
    external_id: Optional[str] = Field(default=None)
    previous_conversation: Optional[str] = Field(default=None)
    context: dict[str, Any] = Field(description="context of the conversation")
    assignee: str
    messages: Optional[list[ChatMessage]] = Field(
        default=None, description="Messages related to the conversations"
    )


class Application(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    workspace_id: str
    unique_name: str
    _normalize_unique_name = field_validator("unique_name")(
        must_be_lowercase_alphanumeric_validator
    )
    aliases: Optional[list[str]]
    extra_instructions: Optional[str]
    provision_schema: Optional[dict]
    created_at: datetime = Field(default_factory=datetime.now)


class PartialApplication(Application, OptionalModel):
    pass


class Directory(BaseModel):
    id: str = Field(default_factory=lambda: generate())
    workspace_id: str
    name: str
    _normalize_name = field_validator("name")(must_be_lowercase_alphanumeric_validator)
    provisioning_config: Optional[dict] = None
    data_owner_config: Optional[dict] = None
    created_by: str
    created_at: datetime = Field(default_factory=datetime.now)


class PartialDirectory(Directory, OptionalModel):
    pass


class Document(BaseModel):
    uuid: str
    custom_id: Optional[str]
    cmetadata: dict
    document: str
    collection_id: str


# Payloads
#


class PaginatedListBase(BaseModel):
    total: int


class PatchOperation(BaseModel):
    op: str = Field(..., description="Operation type")
    path: str = Field(
        ..., description="JSON Pointer path to the element to be operated on"
    )
    value: Optional[Any] = Field(None, description="Value to be used by the operation")
    from_: Optional[str] = Field(
        None, alias="from", description="Source path for move/copy operations"
    )

    immutable_fields: ClassVar[Set[str]] = set(
        ["id", "created_at", "updated_at", "created_by"]
    )
    # can overridden in subclasses for more restrictive behavior
    mutable_fields: ClassVar[Set[str]] = None  # None = all fields are allowed

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str):
        field_name = v.lstrip("/")  # Remove the leading '/' from the path
        if field_name in cls.immutable_fields:
            raise ValueError(f"Modification of '{field_name}' is not allowed")
        if cls.mutable_fields and field_name not in cls.mutable_fields:
            raise ValueError(f"Modification of '{field_name}' is not permitted")
        return v


PatchOperationType = TypeVar("PatchOperationType", bound=PatchOperation)


class JsonPatchDocument(BaseModel, Generic[PatchOperationType]):
    patch: List[PatchOperationType]
