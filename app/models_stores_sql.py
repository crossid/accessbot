from typing import Any, Optional

import sqlalchemy
from fastapi import BackgroundTasks
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    MetaData,
    String,
    Table,
    func,
    select,
)
from sqlalchemy.engine import Engine

from .id import generate
from .models import (
    ChatMessage,
    Conversation,
    ConversationStatuses,
    CurrentUser,
    Workspace,
    WorkspaceStatuses,
)
from .models_stores import (
    ChatMessageStore,
    ConversationStore,
    TransactionContext,
    WorkspaceStore,
)

metadata = MetaData()

WORKSPACE_TABLE_NAME = "workspaces"
CONVERSATION_TABLE_NAME = "conversations"
MESSAGE_TABLE_NAME = "messages"

workspace_table = sqlalchemy.Table(
    WORKSPACE_TABLE_NAME,
    metadata,
    Column("id", String(10), primary_key=True),
    Column("display_name", String(32), nullable=False),
    Column("logo_url", String(), nullable=True),
    Column("status", Enum(WorkspaceStatuses)),
    Column("external_id", String(), nullable=True),
    Column("config", JSON(), nullable=False),
    Column("created_by", String(), nullable=False),
)


conversation_table = sqlalchemy.Table(
    CONVERSATION_TABLE_NAME,
    metadata,
    Column("id", String(10), primary_key=True),
    Column(
        "workspace_id",
        String(10),
        ForeignKey(workspace_table.c.id),
        nullable=False,
        primary_key=True,
    ),
    Column("created_by", String(), nullable=False),
    Column("status", Enum(ConversationStatuses), nullable=False),
    Column("external_id", String(), nullable=True),
    Column("context", JSON(), nullable=False),
    Column("created_at", DateTime(), nullable=False),
)

message_table = sqlalchemy.Table(
    MESSAGE_TABLE_NAME,
    metadata,
    Column("id", String(10), primary_key=True),
    Column(
        "workspace_id",
        String(10),
        ForeignKey(workspace_table.c.id),
        nullable=False,
        primary_key=True,
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


class WorkspaceStoreSQL(WorkspaceStore):
    default_table_name: str = WORKSPACE_TABLE_NAME
    default_conversations_table_name: str = CONVERSATION_TABLE_NAME
    default_messages_table_name = MESSAGE_TABLE_NAME
    metadata: MetaData
    workspaces: Table

    @classmethod
    def build_table(cls, metadata: MetaData, table_name: str) -> Table:
        return workspace_table

    def __init__(
        self,
        table_name: str = default_table_name,
    ):
        self.metadata = metadata
        self.workspaces = self.build_table(
            metadata=self.metadata, table_name=table_name
        )

    def create_tables(self, engine: Engine):
        self.metadata.create_all(engine)

    def get_by_id(
        self, workspace_id: str, tx_context: TransactionContext
    ) -> Optional[Workspace]:
        query = (
            self.workspaces.select()
            .where(
                (self.workspaces.c.id == workspace_id)
                | (self.workspaces.c.external_id == workspace_id)
            )
            .limit(1)
        )
        result: object = tx_context.connection.execute(query).first()
        if result:
            return Workspace(**result._asdict())

    def insert(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ) -> Workspace:
        if workspace.id is None:
            workspace.id = generate()
        o = workspace.model_dump()
        tx_context.connection.execute(self.workspaces.insert(), o)
        return workspace

    def update(
        self,
        workspace: Workspace,
        tx_context: TransactionContext,
    ) -> Workspace:
        q = (
            self.workspaces.update()
            .where(self.workspaces.c.id == workspace.id)
            .values({k: v for k, v in workspace.model_dump().items() if k != "id"})
        )
        tx_context.connection.execute(q)
        return workspace

    def delete(
        self,
        workspace: Workspace,
        current_user: CurrentUser,
        background_tasks: BackgroundTasks,
        tx_context: TransactionContext,
    ):
        q = self.workspaces.delete().where(self.workspaces.c.id == workspace.id)
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
    ):
        self.metadata = metadata
        self.conversations = self.build_conversation_table(
            metadata=self.metadata, table_name=conversations_table_name
        )
        self.messages = self.build_message_table(
            metadata=self.metadata, table_name=messages_table_name
        )

    def create_tables(self, engine: Engine):
        self.metadata.create_all(engine)

    def _get_by(
        self,
        workspace_id: str,
        column: str,
        column_value: any,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        query = (
            self.conversations.select()
            .where(self.conversations.c.workspace_id == workspace_id)
            .where(column == column_value)
            .limit(1)
        )
        result: object = tx_context.connection.execute(query).first()
        conv: Conversation = None
        if result:
            conv = Conversation(**result._asdict())
        if result is None:
            return None
        if links and "messages" in links:
            messages = tx_context.connection.execute(
                self.messages.select().where(self.messages.c.conversation_id == conv.id)
            )
            conv.messages = [ChatMessage(**m._asdict()) for m in messages]
        return conv

    def get_by_id(
        self,
        workspace_id: str,
        conversation_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ):
        return self._get_by(
            workspace_id, self.conversations.c.id, conversation_id, tx_context, links
        )

    def get_by_external_id(
        self,
        workspace_id: str,
        external_id: str,
        tx_context: TransactionContext,
        links: Optional[list[str]] = None,
    ) -> Optional[Conversation]:
        return self._get_by(
            workspace_id,
            self.conversations.c.external_id,
            external_id,
            tx_context,
            links,
        )

    def list(
        self,
        workspace_id: str,
        tx_context: TransactionContext,
        limit: int = 10,
        offset: int = 0,
        filters: dict[str, Any] = None,
        links: Optional[list[str]] = None,
    ) -> tuple[list[Conversation], int]:
        # Query to count total documents
        # Base query for counting
        base_count_query = (
            select(func.count())
            .select_from(self.conversations)
            .where(self.conversations.c.workspace_id == workspace_id)
        )

        # Applying filters to the count query
        if filters:
            for field, value in filters.items():
                base_count_query = base_count_query.where(
                    self.conversations.c[field] == value
                )

        # Execute count query
        total_count = tx_context.connection.execute(base_count_query).scalar_one()

        # Query for retrieving conversations
        query = (
            select(self.conversations)
            .where(self.conversations.c.workspace_id == workspace_id)
            .order_by(self.conversations.c.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if filters:
            for field, value in filters.items():
                query = query.where(self.conversations.c[field] == value)

        result = tx_context.connection.execute(query)
        conversations = []
        for record in result:
            conversation = Conversation(**record._asdict())
            conversations.append(conversation)
            if links and "messages" in links:
                messages_query = select(self.messages).where(
                    self.messages.c.conversation_id == conversation.id
                )
                messages = tx_context.connection.execute(messages_query)
                conversation.messages = [ChatMessage(**m._asdict()) for m in messages]

        # Return both the list of conversations and the total count
        return conversations, total_count

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

    def delete_for_workspace(
        self, workspace_id: str, tx_context: TransactionContext = None
    ):
        if workspace_id is None:
            return None

        q = self.conversations.delete().where(
            self.conversations.c.workspace_id == workspace_id
        )
        tx_context.connection.execute(q)
        return None


class ChatMessageStoreSQL(ChatMessageStore):
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
    ):
        self.metadata = metadata
        self.messages = self.build_table(
            metadata=self.metadata,
            table_name=messages_table_name,
            conversation_table=conversation_table,
        )

    def create_tables(self, engine: Engine):
        self.metadata.create_all(engine)

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

    def delete_for_workspace(
        self, workspace_id: str, tx_context: TransactionContext = None
    ):
        if workspace_id is None:
            return None

        q = self.messages.delete().where(self.messages.c.workspace_id == workspace_id)
        tx_context.connection.execute(q)
        return None
