from sqlalchemy import Engine

from app.ai.sql_chat_message_history import SQLChatMessageHistory
from app.models_facade import ChatMessageFacade


def get_chat_msg_history(
    conversation_id: str, engine: Engine, facade: ChatMessageFacade
):
    chat_history = SQLChatMessageHistory(
        conversation_id=conversation_id,
        engine=engine,
        facade=facade,
    )

    return chat_history
