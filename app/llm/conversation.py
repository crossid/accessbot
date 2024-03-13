# from langchain.globals import set_debug

import json
from typing import Optional

from app.llm.tools.utils import get_tools_for_workspace_and_conversation

from ..embeddings import create_embedding
from ..llm.sql_chat_message_history import LangchainChatMessageHistory
from ..models import Conversation, ConversationTypes, User, Workspace
from ..models_stores import ChatMessageStore
from ..services import factory_ws_store, service_registry
from ..tx import TransactionContext
from ..vector_store import create_retriever
from .agents import create_agent
from .prompts import (
    CONVERSATION_ID_KEY,
    MEMORY_KEY,
    USER_EMAIL_KEY,
    WS_ID_KEY,
    prompt_store,
)

# set_debug(True)


def create_agent_for_access_request_conversation(
    conversation: Conversation, ws: Optional[Workspace], streaming=True
):
    embedding = create_embedding()
    retriever = create_retriever(
        workspace_id=conversation.workspace_id, embedding=embedding
    )

    prompt = None
    if conversation.type == ConversationTypes.recommendation:
        prompt = prompt_store.get("generic_recommendation")
    elif conversation.type == ConversationTypes.data_owner:
        prompt = prompt_store.get("data_owner")
    else:
        raise ValueError("Invalid conversation status")

    data_context = {
        USER_EMAIL_KEY: lambda x: x[USER_EMAIL_KEY],
        WS_ID_KEY: lambda x: x[WS_ID_KEY],
        CONVERSATION_ID_KEY: lambda x: x[CONVERSATION_ID_KEY],
    }

    agent_executor = create_agent(
        retriever=retriever,
        prompt=prompt,
        data_context=data_context,
        tools=get_tools_for_workspace_and_conversation(conv=conversation, ws=ws),
        streaming=streaming,
    )

    return agent_executor


def add_messages(
    chat_history: LangchainChatMessageHistory, user_input: str, ai_content: str
):
    chat_history.add_user_message(user_input)
    chat_history.add_ai_message(ai_content)


async def make_conversation(
    current_user: User,
    conversation: Conversation,
    input: str,
    tx_context: TransactionContext,
):
    message_store = service_registry().get(ChatMessageStore)
    chat_history = LangchainChatMessageHistory(
        conversation_id=conversation.id,
        workspace_id=conversation.workspace_id,
        tx_context=tx_context,
        store=message_store,
    )

    ws_store = factory_ws_store()
    ws = ws_store.get_by_id(
        workspace_id=conversation.workspace_id, tx_context=tx_context
    )

    agent_executor = create_agent_for_access_request_conversation(
        conversation=conversation, ws=ws
    )

    result = await agent_executor.ainvoke(
        {
            "input": input,
            MEMORY_KEY: chat_history.messages,
            USER_EMAIL_KEY: current_user.email,
            WS_ID_KEY: conversation.workspace_id,
            CONVERSATION_ID_KEY: conversation.id,
        },
    )
    add_messages(chat_history, input, result["output"])
    return result


def sse_client_transformer(output: str) -> str:
    event_data = {"content": output}
    event_str = f"event: chat-message\ndata: {json.dumps(event_data)}\n\n"
    return event_str
