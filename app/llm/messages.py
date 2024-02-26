from app.llm.sql_chat_message_history import SQLChatMessageHistory
from app.models_facade import ChatMessageFacade
from app.tx import TransactionContext


def get_chat_msg_history(
    conversation_id: str, tx_context: TransactionContext, facade: ChatMessageFacade
):
    chat_history = SQLChatMessageHistory(
        conversation_id=conversation_id,
        tx_context=tx_context,
        facade=facade,
    )

    return chat_history
