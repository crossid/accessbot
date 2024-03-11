from typing import Any

from langchain_core.tools import StructuredTool, ToolException
from pydantic.v1 import BaseModel, Field, create_model

from app.models import ConversationStatuses, Workspace
from app.services import factory_app_store, factory_conversation_store, factory_ws_store
from app.sql import SQLAlchemyTransactionContext

from .consts import PROVISION_CONFIG_KEY
from .provision.factory import ProvisionerFactory


async def provision_role(
    ws: Workspace, requester_email: str, directory: str, **kwargs
) -> bool:
    config = ws.config[PROVISION_CONFIG_KEY][directory]["config"]

    prov_fact = ProvisionerFactory(
        workspace_id=ws.id,
        type=ws.config[PROVISION_CONFIG_KEY][directory]["type"],
        config=config,
    )
    success = await prov_fact.approve_request(requester_email=requester_email, **kwargs)

    return success


async def _provision_role(
    conversation_id: str,
    user_email: str,
    requester_email: str,
    workspace_id: str,
    directory: str,
    **kwargs,
) -> str:
    directory = directory.lower()
    ws_store = factory_ws_store()
    conv_store = factory_conversation_store()
    with SQLAlchemyTransactionContext().manage() as tx_context:
        ws = ws_store.get_by_id(workspace_id=workspace_id, tx_context=tx_context)

        if ws is not None:
            try:
                success = await provision_role(
                    ws=ws,
                    requester_email=requester_email,
                    directory=directory,
                    **kwargs,
                )
                if success is False:
                    raise ToolException("unknown error")
            except Exception as err:
                raise ToolException(f"failed to request role: {err}")

            # update current request to completed
            updates: dict[str, Any] = {"status": ConversationStatuses.completed.value}
            conv_store.update(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                tx_context=tx_context,
                updates=updates,
            )

        else:
            raise ToolException(f"unknown workspace: {workspace_id}")

    return "role approve completed"


class ApproveRolesInput(BaseModel):
    requester_email: str = Field(
        description="the email of the user who requested the role"
    )
    conversation_id: str = Field(description="the id of the current conversation")
    user_email: str = Field(
        description="the email of the current user in the conversation"
    )
    workspace_id: str = Field(description="workspace id of the current request")
    directory: str = Field(description="directory related to the role")


def create_expanded_model(extra_fields):
    fields = {
        k: (str, Field(description=info["description"]))
        for k, info in extra_fields.items()
    }
    rrt_model = create_model(
        "DynamicApproveRolesInput", __base__=ApproveRolesInput, **fields
    )

    return rrt_model


def create_provision_role_tool(app_id: str, ws_id: str) -> StructuredTool:
    app_store = factory_app_store()
    extra_fields = {"role_name": {"description": "should be a the role name"}}
    with SQLAlchemyTransactionContext().manage() as tx_context:
        app = app_store.get_by_id(
            app_id=app_id, workspace_id=ws_id, tx_context=tx_context
        )
        if app is not None and app.provision_schema is not None:
            extra_fields = app.provision_schema

    dynamic_model = create_expanded_model(extra_fields=extra_fields)

    provision_roles_tool = StructuredTool.from_function(
        func=_provision_role,
        coroutine=_provision_role,
        name="approve_roles",
        description="useful for when you need to approve requested roles by data owner",
        args_schema=dynamic_model,
        return_direct=True,
        handle_tool_error=True,
    )

    return provision_roles_tool
