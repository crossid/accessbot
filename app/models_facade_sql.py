import logging
from typing import Optional

import sqlalchemy
from sqlalchemy import JSON, Column, DateTime, ForeignKey, MetaData, String, Table
from sqlalchemy.engine import Engine

from .id import generate
from .models import ChatMessage, Conversation, ConversationStatuses, Org
from .models_facade import (
    ChatMessageFacade,
    ConversationStore,
    OrgFacade,
    TransactionContext,
)

metadata = MetaData()

ORG_TABLE_NAME = "org"
CONVERSATION_TABLE_NAME = "conversation"
MESSAGE_TABLE_NAME = "message"

org_table = sqlalchemy.Table(
    ORG_TABLE_NAME,
    metadata,
    Column("id", String(10), primary_key=True),
    Column("display_name", String(32), nullable=False),
    Column("external_id", String(), nullable=True),
    Column("config", JSON(), nullable=False),
    Column("creator_id", String(), nullable=False),
)


conversation_table = sqlalchemy.Table(
    CONVERSATION_TABLE_NAME,
    metadata,
    Column("id", String(10), primary_key=True),
    Column(
        "org_id",
        String(10),
        ForeignKey(org_table.c.id),
        nullable=True,
        # This needs to be primary key if we want to distribute the table in cosmosdb. But is also needs to be nullable=False.
        # primary_key=True,
    ),
    Column("created_by", String(), nullable=False),
    Column("status", String(32), nullable=False),
    Column("external_id", String(), nullable=True),
    Column("context", JSON(), nullable=False),
    Column("created_at", DateTime(), nullable=False),
)

message_table = sqlalchemy.Table(
    MESSAGE_TABLE_NAME,
    metadata,
    Column("id", String(10), primary_key=True),
    Column(
        "org_id",
        String(10),
        ForeignKey(org_table.c.id),
        nullable=True,
        # This needs to be primary key if we want to distribute the table in cosmosdb. But is also needs to be nullable=False.
        # primary_key=True,
    ),
    Column(
        "conversation_id",
        String(10),
        # ForeignKey(coversation_table.c.id),
        nullable=False,
    ),
    Column("type", String(32), nullable=False),
    Column("content", String(1024), nullable=True),
    Column("created_at", DateTime(), nullable=False),
)


class OrgFacadeSQL(OrgFacade):
    default_table_name: str = ORG_TABLE_NAME
    default_conversations_table_name: str = CONVERSATION_TABLE_NAME
    default_messages_table_name = MESSAGE_TABLE_NAME
    metadata: MetaData
    orgs: Table

    @classmethod
    def build_table(cls, metadata: MetaData, table_name: str) -> Table:
        return org_table

    def __init__(
        self,
        table_name: str = default_table_name,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.metadata = metadata
        self.orgs = self.build_table(metadata=self.metadata, table_name=table_name)
        self._logger = logger

    def create_tables(self, engine: Engine):
        self.metadata.create_all(engine)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def get_by_id(self, org_id: str, tx_context: TransactionContext) -> Optional[Org]:
        query = (
            self.orgs.select()
            .where((self.orgs.c.id == org_id) | (self.orgs.c.external_id == org_id))
            .limit(1)
        )
        result: object = tx_context.connection.execute(query).first()
        if result:
            return Org(**result._asdict())

    def insert(self, org: Org, tx_context: TransactionContext) -> Org:
        if org.id is None:
            org.id = generate()
        o = org.model_dump()
        tx_context.connection.execute(self.orgs.insert(), o)
        return org

    def delete(self, org: Org, tx_context: TransactionContext):
        q = self.orgs.delete().where(self.orgs.c.id == org.id)
        tx_context.connection.execute(q)

        return None


class ConversationStoreSQL(ConversationStore):
    default_conversations_table_name: str = CONVERSATION_TABLE_NAME
    default_messages_table_name = MESSAGE_TABLE_NAME
    metadata: MetaData
    conversations: Table
    messages: Table

    @classmethod
    def build_conversation_table(cls, metadata: MetaData, table_name: str) -> Table:
        return conversation_table

    @classmethod
    def build_message_table(cls, metadata: MetaData, table_name: str) -> Table:
        return message_table

    def __init__(
        self,
        conversations_table_name: str = default_conversations_table_name,
        messages_table_name: str = default_messages_table_name,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.metadata = metadata
        self.conversations = self.build_conversation_table(
            metadata=self.metadata, table_name=conversations_table_name
        )
        self.messages = self.build_message_table(
            metadata=self.metadata, table_name=messages_table_name
        )
        self._logger = logger

    def create_tables(self, engine: Engine):
        self.metadata.create_all(engine)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def _get_by(
        self,
        org_id: str,
        column: str,
        column_value: any,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        query = (
            self.conversations.select()
            .where(self.conversations.c.org_id == org_id)
            .where(column == column_value)
            .limit(1)
        )
        result: object = tx_context.connection.execute(query).first()
        conv: Conversation = None
        if result:
            conv = Conversation(**result._asdict())
        if links and "messages" in links:
            messages = tx_context.connection.execute(
                self.messages.select().where(self.messages.c.conversation_id == conv.id)
            )
            conv.messages = [ChatMessage(**m._asdict()) for m in messages]
        return conv

    def get_by_id(
        self,
        org_id: str,
        conversation_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ):
        return self._get_by(
            org_id, self.conversations.c.id, conversation_id, tx_context, links
        )

    def get_by_external_id(
        self,
        org_id: str,
        external_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        return self._get_by(
            org_id, self.conversations.c.external_id, external_id, tx_context, links
        )

    def insert(
        self, conversation: Conversation, tx_context: TransactionContext
    ) -> Conversation:
        if conversation.id is None:
            conversation.id = generate()
        conversation.status = ConversationStatuses.active
        o = conversation.model_dump()
        # fixes Error binding parameter 4: type 'StatusEnum' is not supported
        o["status"] = o["status"].value
        tx_context.connection.execute(self.conversations.insert(), o)
        return conversation

    def delete_for_org(self, org_id: str, tx_context: TransactionContext = None):
        if org_id is None:
            return None

        q = self.conversations.delete().where(self.conversations.c.org_id == org_id)
        tx_context.connection.execute(q)
        return None


class ChatMessageFacadeSQL(ChatMessageFacade):
    default_table_name: str = MESSAGE_TABLE_NAME
    metadata: MetaData
    messages: Table

    @classmethod
    def build_table(
        cls, metadata: MetaData, table_name: str, conversation_table: Table
    ) -> Table:
        return message_table

    def __init__(
        self,
        messages_table_name: str = default_table_name,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.metadata = metadata
        self.messages = self.build_table(
            metadata=self.metadata,
            table_name=messages_table_name,
            conversation_table=conversation_table,
        )
        self._logger = logger

    def create_tables(self, engine: Engine):
        self.metadata.create_all(engine)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def list(
        self, filter: None, offset=0, limit=10, tx_context: TransactionContext = None
    ):
        q = (
            self.messages.select()
            .order_by(self.messages.c.created_at.asc())
            .offset(offset)
            .where(self.messages.c.conversation_id == filter)
            .limit(limit)
        )
        result = tx_context.connection.execute(q)
        messages = []
        for record in result:
            messages.append(ChatMessage(**record._asdict()))
        return messages

    def get_by_id(
        self, id: str, tx_context: TransactionContext
    ) -> Optional[ChatMessage]:
        query = self.messages.select().where(self.messages.c.id == id).limit(1)
        result: object = tx_context.connection.execute(query).first()
        if result:
            return ChatMessage(**result._asdict())

    def insert(
        self, message: ChatMessage, tx_context: TransactionContext
    ) -> ChatMessage:
        if message.id is None:
            message.id = generate()
        o = message.model_dump()
        tx_context.connection.execute(self.messages.insert(), o)
        return message

    def delete(self, filter=None, tx_context: TransactionContext = None):
        q = self.messages.delete().where(self.messages.c.conversation_id == filter)
        tx_context.connection.execute(q)
        return None

    def delete_for_org(self, org_id: str, tx_context: TransactionContext = None):
        if org_id is None:
            return None

        q = self.messages.delete().where(self.messages.c.org_id == org_id)
        tx_context.connection.execute(q)
        return None
