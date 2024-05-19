from typing import Any, Optional

from langchain_core.tools import StructuredTool
from pydantic.v1 import BaseModel, Field

from app.models import ConversationStatuses
from app.services import factory_conversation_store
from app.sql import SQLAlchemyTransactionContext


async def _deny_provision(
    conversation_id: str,
    user_email: str,
    requester_email: str,
    workspace_id: str,
    reason: str,
):
    conv_store = factory_conversation_store()
    with SQLAlchemyTransactionContext().manage() as tx_context:
        # update current request to denied
        updates: dict[str, Any] = {"status": ConversationStatuses.denied.value}
        conv_store.update(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            tx_context=tx_context,
            updates=updates,
        )

    return "role deny completed"


class DenyProvisionInput(BaseModel):
    requester_email: str = Field(
        description="the email of the user who requested the role"
    )
    conversation_id: str = Field(description="the id of the current conversation")
    user_email: str = Field(
        description="the email of the current user in the conversation"
    )
    workspace_id: str = Field(description="workspace id of the current request")
    reason: Optional[str] = Field(description="reason given for denying the role")


def create_deny_provision_tool(app_id: str, ws_id: str) -> StructuredTool:
    provision_roles_tool = StructuredTool.from_function(
        func=_deny_provision,
        coroutine=_deny_provision,
        name="deny_access",
        description="useful for when you need to deny requested access",
        args_schema=DenyProvisionInput,
        return_direct=True,
        handle_tool_error=True,
    )

    return provision_roles_tool
