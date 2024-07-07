from langchain_core.tools import StructuredTool, ToolException
from pydantic.v1 import BaseModel, Field, create_model

from app.llm.tools.utils import update_conv
from app.models import ConversationStatuses, Directory
from app.services import (
    factory_app_store,
    factory_conversation_store,
    factory_dir_store,
)
from app.sql import SQLAlchemyTransactionContext

from .provision.factory import ProvisionerFactory


async def provision_role(
    directory: Directory, workspace_id: str, requester_email: str, **kwargs
) -> bool:
    pconfig = directory.provisioning_config
    if pconfig is None:
        raise ValueError(
            f"provisioning config is undefined for directory {directory.name}"
        )

    prov_fact = ProvisionerFactory(
        workspace_id=workspace_id,
        type=pconfig["type"],
        config=pconfig["config"],
    )
    success = await prov_fact.approve_request(requester_email=requester_email, **kwargs)

    return success


def create_summary(
    conv_summary: str, requester_email: str, app_name: str, directory: str, **kwargs
):
    kwargs_str = "\n".join(f"{key}: {value}" for key, value in kwargs.items())
    summary = f"""
        {conv_summary};
        by: {requester_email};
        app: {app_name};
        directory: {directory};
        access: {kwargs_str}
    """

    return summary


async def _provision_role(
    conv_summary: str,
    conversation_id: str,
    user_email: str,
    requester_email: str,
    workspace_id: str,
    app_name: str,
    directory: str,
    **kwargs,
) -> str:
    directory = directory.lower()
    dir_store = factory_dir_store()
    conv_store = factory_conversation_store()
    with SQLAlchemyTransactionContext().manage() as tx_context:
        dir = dir_store.get_by_name(
            name=directory, workspace_id=workspace_id, tx_context=tx_context
        )

        if dir is not None:
            try:
                success = await provision_role(
                    directory=dir,
                    requester_email=requester_email,
                    workspace_id=workspace_id,
                    **kwargs,
                )
                if success is False:
                    raise ToolException("unknown error")
            except Exception as err:
                raise ToolException(f"failed to provision role: {err}")

            # update current request to approved
            update_conv(
                conv_store=conv_store,
                status=ConversationStatuses.approved.value,
                conv_summary=create_summary(
                    conv_summary=conv_summary,
                    requester_email=requester_email,
                    app_name=app_name,
                    directory=directory,
                    **kwargs,
                ),
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                tx_context=tx_context,
            )

        else:
            raise ToolException(f"unknown directory: {directory}")

    return f"role approved for {requester_email} successfully"


class ApproveRolesInput(BaseModel):
    conv_summary: str = Field(
        description="should be a summary of the conversation with the user"
    )
    requester_email: str = Field(
        description="the email of the user who requested the role"
    )
    conversation_id: str = Field(description="the id of the current conversation")
    user_email: str = Field(
        description="the email of the current user in the conversation"
    )
    workspace_id: str = Field(description="workspace id of the current request")
    app_name: str = Field(description="name of the application the user needs access")
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
    extra_fields = {"access_id": {"description": "should be a the access id"}}
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
        handle_tool_error=True,
    )

    return provision_roles_tool
