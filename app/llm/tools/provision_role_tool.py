from typing import Any

from app.models import ConversationStatuses, Workspace
from app.services import (
    factory_conversation_store,
    factory_ws_store,
)
from app.sql import SQLAlchemyTransactionContext
from langchain_core.tools import StructuredTool, ToolException
from pydantic.v1 import BaseModel, Field

from .consts import PROVISION_CONFIG_KEY
from .provision.factory import ProvisionerFactory


class ApproveRolesInput(BaseModel):
    role_name: str = Field(description="should be a the role name")
    requester_email: str = Field(
        description="the email of the user who requested the role"
    )
    conversation_id: str = Field(description="the id of the current conversation")
    user_email: str = Field(
        description="the email of the current user in the conversation"
    )
    workspace_id: str = Field(description="workspace id of the current request")


async def provision_role(ws: Workspace, role_name: str, requester_email: str) -> bool:
    directory_role_name = role_name.split("/")
    if len(directory_role_name) < 3:
        raise ValueError("No directory provided")
    directory = directory_role_name[0]
    role_name = directory_role_name.pop()
    config = ws.config[PROVISION_CONFIG_KEY][directory]["config"]

    prov_fact = ProvisionerFactory(
        workspace_id=ws.id,
        type=ws.config[PROVISION_CONFIG_KEY][directory]["type"],
        config=config,
    )
    success = await prov_fact.approve_request(
        rolename=role_name, requester_email=requester_email
    )

    return success


async def _provision_role(
    role_name: str,
    conversation_id: str,
    user_email: str,
    requester_email: str,
    workspace_id: str,
) -> str:
    ws_store = factory_ws_store()
    conv_store = factory_conversation_store()
    with SQLAlchemyTransactionContext().manage() as tx_context:
        ws = ws_store.get_by_id(workspace_id=workspace_id, tx_context=tx_context)

        if ws is not None:
            try:
                success = await provision_role(
                    ws=ws, role_name=role_name, requester_email=requester_email
                )
                if success is False:
                    raise ToolException("unknown error")
            except Exception as err:
                raise ToolException(f"failed to request role: {err}")

            # update current request to completed
            updates: dict[str, Any] = {"status": ConversationStatuses.completed.value}
            updated_conv = conv_store.update(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                tx_context=tx_context,
                updates=updates,
            )

            # update previous request to completed
            conv_store.update(
                workspace_id=workspace_id,
                conversation_id=updated_conv.external_id,
                tx_context=tx_context,
                updates=updates,
            )

        else:
            raise ToolException(f"unknown workspace: {workspace_id}")

    return "role approve completed"


provision_roles = StructuredTool.from_function(
    func=_provision_role,
    coroutine=_provision_role,
    name="approve_roles",
    description="useful for when you need to approve requested roles by data owner",
    args_schema=ApproveRolesInput,
    return_direct=True,
    handle_tool_error=True,
)
