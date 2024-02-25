import logging
from datetime import datetime
from typing import List

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    message_to_dict,
)
from sqlalchemy import Engine

from app.models import ChatMessage
from app.models_facade import ChatMessageFacade
from app.sql import SQLAlchemyTransactionContext

logger = logging.getLogger(__name__)


class SQLChatMessageHistory(BaseChatMessageHistory):
    """Chat message history stored in an SQL database."""

    def __init__(
        self,
        conversation_id: str,
        engine: Engine,
        facade: ChatMessageFacade,
    ):
        self.conversation_id = conversation_id
        self.engine = engine
        self.facade = facade

    def message_to_dict(self, msg: BaseMessage) -> dict:
        return message_to_dict(msg)

    def from_sql_model(self, sql_message: ChatMessage) -> BaseMessage:
        if sql_message.type == "human":
            return HumanMessage(
                content=sql_message.content,
            )
        elif sql_message.type == "ai":
            return AIMessage(
                content=sql_message.content,
            )
        elif sql_message.type == "system":
            return SystemMessage(
                content=sql_message.content,
            )
        else:
            raise ValueError(f"Unknown message type: {sql_message.type}")

    def to_sql_model(self, msg: BaseMessage) -> ChatMessage:
        return ChatMessage(
            conversation_id=self.conversation_id,
            type=msg.type,
            content=msg.content,
            created_at=datetime.now(),
        )

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx:
            messages = []
            result = self.facade.list(filter=self.conversation_id, tx_context=tx)
            for record in result:
                messages.append(self.from_sql_model(record))
            return messages

    def add_message(self, message: BaseMessage) -> None:
        """Append the message to the record in db"""
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx:
            d = self.to_sql_model(message)
            self.facade.insert(d, tx)
        logger.debug(f"Added message to chat history: {message.content}")

    def clear(self) -> None:
        """Clear session memory from db"""
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx:
            self.facade.delete(filter=self.conversation_id, tx_context=tx)
