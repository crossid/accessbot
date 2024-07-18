from langchain_core.tools import StructuredTool, ToolException

from app.llm.tools.utils import create_expanded_model, update_conv
from app.models import ConversationStatuses, Directory
from app.services import (
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


approve_roles_input_dict = {
    "conv_summary": {
        "type": str,
        "description": "should be a summary of the conversation with the user",
    },
    "requester_email": {
        "type": str,
        "description": "the email of the user who requested the role",
    },
    "conversation_id": {
        "type": str,
        "description": "the id of the current conversation",
    },
    "user_email": {
        "type": str,
        "description": "the email of the current user in the conversation",
    },
    "workspace_id": {"type": str, "description": "workspace id of the current request"},
    "app_name": {
        "type": str,
        "description": "name of the application the user needs access",
    },
    "directory": {"type": str, "description": "directory related to the role"},
}


def create_provision_role_tool(app_id: str, ws_id: str) -> StructuredTool:
    default_extra_fields = {"access_id": {"description": "should be a the access id"}}

    dynamic_model = create_expanded_model(
        app_id=app_id,
        ws_id=ws_id,
        base_model=approve_roles_input_dict,
        model_name="ApproveRolesInput",
        default_extra_fields=default_extra_fields,
    )

    provision_roles_tool = StructuredTool.from_function(
        func=_provision_role,
        coroutine=_provision_role,
        name="approve_roles",
        description="useful for when you need to approve requested roles by data owner",
        args_schema=dynamic_model,
        handle_tool_error=True,
    )

    return provision_roles_tool
