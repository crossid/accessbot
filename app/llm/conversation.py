# from langchain.globals import set_debug


from ..embeddings import create_embedding
from ..llm.sql_chat_message_history import LangchainChatMessageHistory
from ..models import Conversation, ConversationStatuses, User
from ..services import message_facade
from ..tx import TransactionContext
from ..vector_store import create_retriever
from .agents import create_agent
from .prompts import (
    CONVERSATION_ID_KEY,
    MEMORY_KEY,
    ORGID_KEY,
    USERNAME_KEY,
    prompt_facade,
)

# set_debug(True)


def create_agent_for_access_request_conversation(
    conversation: Conversation, streaming=True
):
    embedding = create_embedding()
    retriever = create_retriever(org_id=conversation.org_id, embedding=embedding)

    prompt = None
    if conversation.status == ConversationStatuses.active:
        prompt = prompt_facade.get("generic_recommendation")
    else:
        raise ValueError("Invalid conversation status")

    data_context = {
        USERNAME_KEY: lambda x: x[USERNAME_KEY],
        ORGID_KEY: lambda x: x[ORGID_KEY],
        CONVERSATION_ID_KEY: lambda x: x[CONVERSATION_ID_KEY],
    }

    agent_executor = create_agent(
        retriever=retriever,
        prompt=prompt,
        data_context=data_context,
        tools=[],
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
    chat_history = LangchainChatMessageHistory(
        conversation_id=conversation.id,
        org_id=conversation.org_id,
        tx_context=tx_context,
        facade=message_facade,
    )

    agent_executor = create_agent_for_access_request_conversation(conversation)
    result = await agent_executor.ainvoke(
        {
            "input": input,
            MEMORY_KEY: chat_history.messages,
            USERNAME_KEY: current_user.id,
            ORGID_KEY: conversation.org_id,
            CONVERSATION_ID_KEY: conversation.id,
        },
    )
    add_messages(chat_history, input, result["output"])
    return result


def sse_client_transformer(output: str) -> str:
    event_str = f"event: chat-message\ndata: {output}\n\n"
    return event_str
