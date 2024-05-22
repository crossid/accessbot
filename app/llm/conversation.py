# from langchain.globals import set_debug
import json
from typing import Any, Optional

from langchain_core.messages import HumanMessage
from langgraph.checkpoint import BaseCheckpointSaver

from app.llm.tools.utils import get_tools_for_workspace_and_conversation

from ..embeddings import create_embedding
from ..llm.graph import CONVERSATION_TYPE_KEY
from ..llm.sql_chat_message_history import LangchainChatMessageHistory
from ..models import Application, Conversation, User, Workspace
from ..models_stores import ChatMessageStore
from ..services import (
    factory_app_store,
    factory_checkpointer,
    factory_ws_store,
    service_registry,
)
from ..tx import TransactionContext
from ..vector_store import create_retriever
from .graph import create_graph
from .prompts import (
    CONVERSATION_ID_KEY,
    KNOWN_APPS_KEY,
    MEMORY_KEY,
    USER_EMAIL_KEY,
    WS_ID_KEY,
)

# set_debug(True)


def create_agent_for_access_request_conversation(
    conversation: Conversation,
    ws: Optional[Workspace],
    data_context: dict[str, Any],
    checkpointer: BaseCheckpointSaver = None,
):
    embedding = create_embedding()
    retriever = create_retriever(
        workspace_id=conversation.workspace_id, embedding=embedding
    )

    if checkpointer is None:
        checkpointer = factory_checkpointer()

    graph = create_graph(
        tools=get_tools_for_workspace_and_conversation(conv=conversation, ws=ws),
        data_context=data_context,
        retriever=retriever,
        checkpointer=checkpointer,
    )

    return graph


def add_messages(
    chat_history: LangchainChatMessageHistory, user_input: str, ai_content: str
):
    chat_history.add_user_message(user_input)
    chat_history.add_ai_message(ai_content)


def prepare_known_apps_str(apps: list[Application]):
    app_str = []
    for app in apps:
        app_str.append(f"{app.display_name} - aka {', '.join(app.aliases)};")

    return "\n".join(app_str)


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

    app_store = factory_app_store()
    apps, _ = app_store.list(workspace_id=ws.id, limit=1000, tx_context=tx_context)

    dc = {
        USER_EMAIL_KEY: current_user.email,
        WS_ID_KEY: conversation.workspace_id,
        CONVERSATION_ID_KEY: conversation.id,
        KNOWN_APPS_KEY: prepare_known_apps_str(apps=apps),
    }

    agent_executor = create_agent_for_access_request_conversation(
        conversation=conversation, ws=ws, data_context=dc
    )

    config = {
        "configurable": {
            "thread_id": conversation.id,
            "workspace_id": conversation.workspace_id,
        }
    }

    result = await agent_executor.ainvoke(
        {
            MEMORY_KEY: [HumanMessage(content=input)],
            CONVERSATION_TYPE_KEY: conversation.type.value,
        },
        config,
    )
    last_message = result[MEMORY_KEY][-1].content
    add_messages(chat_history, input, last_message)
    return {"output": last_message}


def sse_client_transformer(
    output: str, llm_name: str, event_type: str = "chat-message"
) -> str:
    event_data = {"content": output, "name": llm_name}
    event_str = f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
    return event_str
