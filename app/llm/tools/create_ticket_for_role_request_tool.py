import logging
from typing import Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import StructuredTool, ToolException
from langgraph.checkpoint.base import CheckpointMetadata, empty_checkpoint

from app.consts import TICKET_SYSTEM_CONFIG_KEY
from app.llm.prompts import MEMORY_KEY
from app.llm.sql_chat_message_history import LangchainChatMessageHistory
from app.llm.tools.provision_role_tool import provision_role
from app.llm.tools.rule_engine.rule_engine_agent import FinalAnswer, should_auto_approve
from app.llm.tools.utils import create_expanded_model, get_do_msg_content, update_conv
from app.models import (
    Conversation,
    ConversationStatuses,
    ConversationTypes,
    User,
    Workspace,
)
from app.services import (
    factory_app_store,
    factory_checkpointer,
    factory_conversation_store,
    factory_dir_store,
    factory_message_store,
    factory_user_store,
    factory_ws_store,
)
from app.sql import SQLAlchemyTransactionContext

from .create_ticket.factory import TicketSystemFactory
from .data_owner.factory import get_data_owner

logger = logging.getLogger(__name__)


async def make_request(
    ws: Workspace,
    owner: Optional[User],
    output: str,
    requester: User,
    conv_summary: str,
    conversation_id: str,
    app_name: str,
    **kwargs,
) -> str:
    ts = TicketSystemFactory(ws=ws)
    if ts is None:
        return ""

    # Owner might be none, so the ticket creation has to be defensive if it needs an owner
    ticket_id = ts.create_ticket(
        content=output,
        owner=owner,
        requester=requester,
        conv_summary=conv_summary,
        conversation_id=conversation_id,
        workspace_id=ws.id,
        app_name=app_name,
        **kwargs,
    )

    return ticket_id


async def _request_roles(
    conv_summary: str,
    conv_lang: str,
    conversation_id: str,
    user_email: str,
    workspace_id: str,
    app_name: str,
    directory: str,
    **kwargs,
) -> str:
    directory = directory.lower()
    output = f"requester:{user_email}; directory: {directory}; app name: {app_name}; summary: {conv_summary}"

    user_store = factory_user_store()
    current_user = user_store.get_by_email(email=user_email)
    ws_store = factory_ws_store()
    dir_store = factory_dir_store()
    app_store = factory_app_store()
    conv_store = factory_conversation_store()
    with SQLAlchemyTransactionContext().manage() as tx_context:
        dir = dir_store.get_by_name(
            name=directory, workspace_id=workspace_id, tx_context=tx_context
        )

        if dir is None:
            return "request failed, use recommender"

        ws = ws_store.get_by_id(workspace_id=workspace_id, tx_context=tx_context)
        if ws is not None:
            app = app_store.get_by_name(
                app_name=app_name, workspace_id=workspace_id, tx_context=tx_context
            )

            if app is None:
                return "use recommender"

            try:
                answer = await should_auto_approve(
                    ws=ws, dir=dir, app=app, user_email=user_email, **kwargs
                )
                if answer.final_answer == FinalAnswer.approve:
                    logger.debug(f"access approved automatically because: {answer.why}")
                    success = await provision_role(
                        directory=dir,
                        workspace_id=ws.id,
                        requester_email=user_email,
                        **kwargs,
                    )
                    if success:
                        update_conv(
                            conv_store=conv_store,
                            status=ConversationStatuses.approved.value,
                            conv_summary=conv_summary,
                            workspace_id=workspace_id,
                            conversation_id=conversation_id,
                            tx_context=tx_context,
                        )
                        return "access approved automatically"
                    else:
                        raise ToolException(
                            "failed to provision access for unknown reason"
                        )

                owner = await get_data_owner(
                    ws=ws, app_name=app_name, directory=dir, **kwargs
                )
                ticket_id = await make_request(
                    ws=ws,
                    owner=owner,
                    output=output,
                    app_name=app_name,
                    requester=current_user,
                    conversation_id=conversation_id,
                    conv_summary=conv_summary,
                    conv_lang=conv_lang,
                    **kwargs,
                )
            except Exception as err:
                raise ToolException(f"failed to open a ticket: {err}")

        # create new conversation for data owner
        do_conv = Conversation(
            workspace_id=workspace_id,
            external_id=ticket_id,
            type=ConversationTypes.data_owner.value,
            assignee=owner.email,
            previous_conversation=conversation_id,
            context={
                "communication_channel": ws.config.get(
                    TICKET_SYSTEM_CONFIG_KEY, {}
                ).get("type", "portal")
            },
        )
        new_do_conv = conv_store.insert(conversation=do_conv, tx_context=tx_context)

        kwargs_str = "\n".join(f"{key}: {value}" for key, value in kwargs.items())
        msg = get_do_msg_content(
            lang=conv_lang,
            requester=user_email,
            app_name=app_name,
            conv_summary=conv_summary,
            **kwargs,
        )

        message_store = factory_message_store()
        chat_history = LangchainChatMessageHistory(
            conversation_id=new_do_conv.id,
            workspace_id=new_do_conv.workspace_id,
            tx_context=tx_context,
            store=message_store,
        )

        chat_history.add_ai_message(message=msg.full)

        checkpoint = empty_checkpoint()
        sys_msg = f"requester: {user_email}.\nprevious conversation summary: {conv_summary}.\ndirectory: {directory}\napp_id: {app.id}\napp_name: {app_name}\n{kwargs_str}"
        checkpoint["channel_values"] = {
            MEMORY_KEY: [
                SystemMessage(content=sys_msg),
                AIMessage(content=msg.approval_q),
            ]
        }
        cmetadata = CheckpointMetadata()
        cmetadata["source"] = "update"

        checkpointer = factory_checkpointer()
        config = {
            "configurable": {
                "thread_id": new_do_conv.id,
                "workspace_id": new_do_conv.workspace_id,
            }
        }
        await checkpointer.aput(config, checkpoint, cmetadata)

        # update conversation to completed
        update_conv(
            conv_store=conv_store,
            status=ConversationStatuses.completed.value,
            conv_summary=conv_summary,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            tx_context=tx_context,
        )

    return "conversation ended"


rri = {
    "conv_summary": {
        "type": str,
        "description": "should be a summary of the conversation with the user",
    },
    "conv_lang": {
        "type": str,
        "description": "ISO 639 language code of the conversation",
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
    "directory": {"type": str, "description": "directory related to the roles"},
}


def create_request_roles_tool(app_id: str, ws_id: str):
    default_extra_fields = {
        "access_id": {
            "description": "should be a the recommended access identifier deduced from the conversation"
        }
    }

    dynamic_model = create_expanded_model(
        app_id=app_id,
        ws_id=ws_id,
        base_model=rri,
        model_name="RequestRolesInput",
        default_extra_fields=default_extra_fields,
    )
    request_roles_tool = StructuredTool.from_function(
        func=_request_roles,
        coroutine=_request_roles,
        name="request_access",
        description="useful for when you need to request access",
        args_schema=dynamic_model,
        handle_tool_error=True,
    )

    return request_roles_tool
