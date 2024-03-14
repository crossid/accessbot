from typing import Any, Optional

from langchain_core.tools import StructuredTool, ToolException
from pydantic.v1 import BaseModel, Field

from app.llm.sql_chat_message_history import LangchainChatMessageHistory
from app.models import (
    Conversation,
    ConversationStatuses,
    ConversationTypes,
    User,
    Workspace,
)
from app.services import (
    factory_conversation_store,
    factory_message_store,
    factory_user_store,
    factory_ws_store,
)
from app.sql import SQLAlchemyTransactionContext

from .consts import TICKET_SYSTEM_CONFIG_KEY
from .create_ticket.factory import TicketSystemFactory
from .data_owner.factory import get_data_owner


async def make_request(
    ws: Workspace,
    owner: Optional[User],
    output: str,
    role_name: str,
    requester: User,
    access: str,
    conv_summary: str,
    conversation_id: str,
):
    ts = TicketSystemFactory(
        workspace_id=ws.id,
        type=ws.config[TICKET_SYSTEM_CONFIG_KEY]["type"],
        config=ws.config[TICKET_SYSTEM_CONFIG_KEY]["config"],
    )
    # Owner might be none, so the ticket creation has to be defensive if it needs an owner
    ts.create_ticket(
        content=output,
        owner=owner,
        requester=requester,
        access=access,
        conv_summary=conv_summary,
        role_name=role_name,
        conversation_id=conversation_id,
        workspace_id=ws.id,
    )


class RequestRolesInput(BaseModel):
    role_name: str = Field(
        description="should be the full role name, including the directory"
    )
    access: str = Field(
        description="should be a the access the user requested in the conversation"
    )
    conv_summary: str = Field(
        description="should be a summary of the conversation with the user"
    )
    conversation_id: str = Field(description="the id of the current conversation")
    user_email: str = Field(
        description="the email of the current user in the conversation"
    )
    workspace_id: str = Field(description="workspace id of the current request")
    directory: str = Field(description="directory related to the role")


async def _request_roles(
    role_name: str,
    access: str,
    conv_summary: str,
    conversation_id: str,
    user_email: str,
    workspace_id: str,
    directory: str,
) -> str:
    directory = directory.lower()
    output = f"by:{user_email}; directory: {directory}; role_name: {role_name}; access: {access}; summary: {conv_summary}"

    user_store = factory_user_store()
    current_user = user_store.get_by_email(email=user_email)
    ws_store = factory_ws_store()
    conv_store = factory_conversation_store()
    with SQLAlchemyTransactionContext().manage() as tx_context:
        ws = ws_store.get_by_id(workspace_id=workspace_id, tx_context=tx_context)
        if ws is not None:
            try:
                owner = await get_data_owner(
                    ws=ws, role_name=role_name, directory=directory
                )
                await make_request(
                    ws=ws,
                    owner=owner,
                    output=output,
                    role_name=role_name,
                    requester=current_user,
                    conversation_id=conversation_id,
                    access=access,
                    conv_summary=conv_summary,
                )
            except Exception as err:
                raise ToolException(f"failed to open a ticket: {err}")

        # create new conversation for data owner
        do_conv = Conversation(
            workspace_id=workspace_id,
            external_id=conversation_id,
            type=ConversationTypes.data_owner,
            created_by=owner.id,
            context={
                "communication_channel": ws.config[TICKET_SYSTEM_CONFIG_KEY]["type"]
            },
        )
        conv_store.insert(conversation=do_conv, tx_context=tx_context)

        message_store = factory_message_store()
        chat_history = LangchainChatMessageHistory(
            conversation_id=do_conv.id,
            workspace_id=do_conv.workspace_id,
            tx_context=tx_context,
            store=message_store,
        )
        chat_history.add_ai_message(
            message=f"hello, there's a new request waiting for you:\n {output}.\n Would you like to approve it?"
        )

        # update conversation to submitted
        updates: dict[str, Any] = {"status": ConversationStatuses.submitted.value}
        conv_store.update(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            updates=updates,
            tx_context=tx_context,
        )

    return "conversation ended"


request_roles = StructuredTool.from_function(
    func=_request_roles,
    coroutine=_request_roles,
    name="request_roles",
    description="useful for when you need to request roles",
    args_schema=RequestRolesInput,
    return_direct=False,
    handle_tool_error=True,
)
