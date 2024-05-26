import pickle
from datetime import datetime
from typing import Any, AsyncIterator, List, Optional

import sqlalchemy
from fastapi import BackgroundTasks, HTTPException
from langchain_core.runnables import ConfigurableFieldSpec, RunnableConfig
from langgraph.checkpoint import BaseCheckpointSaver
from langgraph.checkpoint.base import (
    Checkpoint,
    CheckpointThreadTs,
    CheckpointTuple,
)
from pydantic_core import ErrorDetails
from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
    MetaData,
    String,
    Table,
    Text,
    cast,
    func,
    or_,
    select,
)
from sqlalchemy.engine import Engine

from .id import generate
from .models import (
    Application,
    ChatMessage,
    Conversation,
    ConversationStatuses,
    ConversationTypes,
    CurrentUser,
    Workspace,
    WorkspaceStatuses,
)
from .models_stores import (
    ApplicationStore,
    ChatMessageStore,
    ConversationStore,
    TransactionContext,
    WorkspaceStore,
)

metadata = MetaData()

WORKSPACE_TABLE_NAME = "workspaces"
CONVERSATION_TABLE_NAME = "conversations"
MESSAGE_TABLE_NAME = "messages"
APPLICATIONS_TABLE_NAME = "applications"
CHECKPOINT_TABLE_NAME = "checkpoints"

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
    Column("assignee", String(), nullable=False),
    Column("type", Enum(ConversationTypes), nullable=False),
    Column("status", Enum(ConversationStatuses), nullable=False),
    Column("external_id", String(), nullable=True),
    Column("previous_conversation", String(), nullable=True),
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

checkpoint_table = sqlalchemy.Table(
    CHECKPOINT_TABLE_NAME,
    metadata,
    Column("thread_id", String(10), primary_key=True),
    Column("thread_ts", TIMESTAMP(), primary_key=True),
    Column("parent_ts", TIMESTAMP(), primary_key=False, nullable=True),
    Column(
        "workspace_id",
        String(10),
        ForeignKey(workspace_table.c.id),
        nullable=False,
    ),
    Column("checkpoint", LargeBinary()),
    Column("metadata", JSON()),
)

applications_table = sqlalchemy.Table(
    APPLICATIONS_TABLE_NAME,
    metadata,
    Column("id", String(10), primary_key=True),
    Column(
        "workspace_id",
        String(10),
        ForeignKey(workspace_table.c.id),
        nullable=False,
    ),
    Column("unique_name", String(), nullable=False),
    Column("aliases", JSON(), nullable=False),
    Column("extra_instructions", String(), nullable=True),
    Column("provision_schema", JSON(), nullable=True),
)

Index(
    "ix_ws_un",
    applications_table.c.workspace_id,
    applications_table.c.unique_name,
    unique=True,
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

    def update(
        self,
        workspace_id: str,
        conversation_id: str,
        updates: dict[str, Any],
        tx_context: TransactionContext,
    ) -> Conversation:
        q = (
            self.conversations.update()
            .where(self.conversations.c.id == conversation_id)
            .where(self.conversations.c.workspace_id == workspace_id)
            .values(updates)
        )

        tx_context.connection.execute(q)
        return self.get_by_id(
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            tx_context=tx_context,
        )

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


class ApplicationStoreSQL(ApplicationStore):
    default_table_name: str = APPLICATIONS_TABLE_NAME
    metadata: MetaData
    apps: Table

    @classmethod
    def build_table(
        cls, metadata: MetaData, table_name: str, apps_table: Table
    ) -> Table:
        return applications_table

    def __init__(
        self,
        apps_table_name: str = default_table_name,
    ):
        self.metadata = metadata
        self.apps = self.build_table(
            metadata=self.metadata,
            table_name=apps_table_name,
            apps_table=applications_table,
        )

    def create_tables(self, engine: Engine):
        self.metadata.create_all(engine)

    def list(
        self,
        workspace_id: str,
        filters: dict[str, Any] = None,
        offset=0,
        limit=10,
        tx_context: TransactionContext = None,
        projection: List[str] = [],
    ) -> tuple[list[Application], int]:
        base_count_query = (
            select(func.count())
            .select_from(self.apps)
            .where(self.apps.c.workspace_id == workspace_id)
        )

        # Applying filters to the count query
        if filters:
            for field, value in filters.items():
                base_count_query = base_count_query.where(self.apps.c[field] == value)

        # Execute count query
        total_count = tx_context.connection.execute(base_count_query).scalar_one()

        columns = [
            self.apps.c[column_name]
            for column_name in projection
            if column_name in self.apps.c
        ]
        query = (
            select(*columns if len(columns) > 0 else self.apps.c)
            .where(self.apps.c.workspace_id == workspace_id)
            .order_by(self.apps.c.unique_name.asc())
            .offset(offset)
            .limit(limit)
        )

        if filters:
            for field, value in filters.items():
                query = query.where(self.apps.c[field] == value)

        result = tx_context.connection.execute(query)
        apps = []
        for record in result:
            app = Application.from_db_record(record)
            apps.append(app)

        return apps, total_count

    def get_by_id(
        self, app_id: str, workspace_id: str, tx_context: TransactionContext
    ) -> Optional[Application]:
        query = (
            self.apps.select()
            .where(self.apps.c.id == app_id)
            .where(self.apps.c.workspace_id == workspace_id)
            .limit(1)
        )

        result: object = tx_context.connection.execute(query).first()
        if result:
            return Application(**result._asdict())

    def get_by_name(
        self, app_name: str, workspace_id: str, tx_context: TransactionContext
    ) -> Optional[Application]:
        query = (
            self.apps.select()
            .where(self.apps.c.workspace_id == workspace_id)
            .where(
                or_(
                    self.apps.c.unique_name.ilike(app_name),
                    cast(self.apps.c.aliases, Text).ilike(f"%{app_name}%"),
                )
            )
            .limit(1)
        )

        result: object = tx_context.connection.execute(query).first()
        if result:
            return Application(**result._asdict())

    def insert(self, app: Application, tx_context: TransactionContext) -> Application:
        query = (
            self.apps.select()
            .where(self.apps.c.workspace_id == app.workspace_id)
            .where(self.apps.c.unique_name == app.unique_name)
            .limit(1)
        )

        result: object = tx_context.connection.execute(query).first()
        if result:
            error = ErrorDetails(
                type="uniqueness",
                loc=("body", "unique_name"),
                msg=f"unique_name '{app.unique_name}' already exists",
            )
            raise HTTPException(status_code=409, detail=[error])

        if app.id is None:
            app.id = generate()
        o = app.model_dump()
        tx_context.connection.execute(self.apps.insert(), o)
        return app

    def delete(
        self,
        workspace_id: str,
        app_id: str,
        tx_context: TransactionContext,
    ):
        q = (
            self.apps.delete()
            .where(self.apps.c.id == app_id)
            .where(self.apps.c.workspace_id == workspace_id)
        )
        tx_context.connection.execute(q)
        return None

    def update(
        self,
        application: Application,
        tx_context: TransactionContext,
    ) -> Workspace:
        q = (
            self.apps.update()
            .where(self.apps.c.id == application.id)
            .values({k: v for k, v in application.model_dump().items() if k != "id"})
        )
        tx_context.connection.execute(q)
        return application

    def delete_for_workspace(
        self, workspace_id: str, tx_context: TransactionContext = None
    ) -> None:
        if workspace_id is None:
            return None

        q = self.apps.delete().where(self.apps.c.workspace_id == workspace_id)
        tx_context.connection.execute(q)
        return None


class CheckpointStoreSQL(BaseCheckpointSaver):
    class Config:
        arbitrary_types_allowed = True

    default_table_name: str = CHECKPOINT_TABLE_NAME
    metadata: MetaData = metadata
    checkpoints: Table = checkpoint_table
    engine: Engine

    @classmethod
    def build_table(cls, metadata: MetaData, table_name: str) -> Table:
        return checkpoint_table

    def create_tables(self, engine: Engine):
        self.metadata.create_all(engine)

    def __init__(self, engine: Engine):
        super().__init__(engine=engine)
        self.engine = engine

    @property
    def config_specs(self) -> list[ConfigurableFieldSpec]:
        return [
            ConfigurableFieldSpec(
                id="thread_id",
                annotation=Optional[str],
                name="Thread ID",
                description=None,
                default=None,
                is_shared=True,
            ),
            ConfigurableFieldSpec(
                id="workspace_id",
                annotation=Optional[str],
                name="Workspace ID",
                description=None,
                default=None,
                is_shared=True,
            ),
            CheckpointThreadTs,
        ]

    def get(self, config: RunnableConfig) -> Optional[Checkpoint]:
        raise NotImplementedError

    def put(self, config: RunnableConfig, checkpoint: Checkpoint) -> RunnableConfig:
        raise NotImplementedError

    async def alist(self, config: RunnableConfig) -> AsyncIterator[CheckpointTuple]:
        with self.engine.connect() as conn:
            thread_id = config["configurable"]["thread_id"]
            workspace_id = config["configurable"]["workspace_id"]
            query = (
                select(self.checkpoints)
                .where(self.checkpoints.c.workspace_id == workspace_id)
                .where(self.checkpoints.c.thread_id == thread_id)
                .order_by(self.checkpoints.c.thread_ts.desc())
            )

            result = conn.execute(query).all()
            tuples = []

            for record in result:
                rdict = record._asdict()
                tuple = CheckpointTuple(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "thread_ts": rdict["thread_ts"],
                            "workspace_id": workspace_id,
                        }
                    },
                    pickle.loads(rdict["checkpoint"]),
                    # rdict["metadata"],
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "thread_ts": rdict["parent_ts"],
                            "workspace_id": workspace_id,
                        }
                    }
                    if rdict.get("parent_ts")
                    else None,
                )
                tuples.append(tuple)

            return tuples

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        workspace_id = config["configurable"]["workspace_id"]
        thread_ts = config["configurable"].get("thread_ts")
        with self.engine.connect() as conn:
            if thread_ts:
                query = (
                    select(self.checkpoints)
                    .where(self.checkpoints.c.workspace_id == workspace_id)
                    .where(self.checkpoints.c.thread_id == thread_id)
                    .where(
                        self.checkpoints.c.thread_ts
                        == datetime.fromisoformat(thread_ts)
                    )
                )

                value = conn.execute(query).fetchone()
                if value:
                    vdict = value._asdict()
                    return CheckpointTuple(
                        config,
                        pickle.loads(vdict["checkpoint"]),
                        # vdict["metadata"],
                        {
                            "configurable": {
                                "thread_id": thread_id,
                                "thread_ts": vdict.get("parent_ts"),
                                "workspace_id": workspace_id,
                            }
                        }
                        if vdict.get("parent_ts")
                        else None,
                    )
            else:
                query = (
                    select(self.checkpoints)
                    .where(self.checkpoints.c.workspace_id == workspace_id)
                    .where(self.checkpoints.c.thread_id == thread_id)
                    .order_by(self.checkpoints.c.thread_ts.desc())
                )

                value = conn.execute(query).fetchone()
                if value:
                    vdict = value._asdict()
                    return CheckpointTuple(
                        {
                            "configurable": {
                                "thread_id": thread_id,
                                "thread_ts": vdict.get("thread_ts"),
                                "workspace_id": workspace_id,
                            }
                        },
                        pickle.loads(vdict["checkpoint"]),
                        # vdict["metadata"],
                        {
                            "configurable": {
                                "thread_id": thread_id,
                                "thread_ts": vdict.get("parent_ts"),
                                "workspace_id": workspace_id,
                            }
                        }
                        if vdict.get("parent_ts")
                        else None,
                    )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        # metadata: CheckpointMetadata,
    ) -> None:
        thread_id = config["configurable"]["thread_id"]
        workspace_id = config["configurable"]["workspace_id"]
        with self.engine.connect() as conn:
            record = {
                "thread_id": thread_id,
                "workspace_id": workspace_id,
                "thread_ts": datetime.fromisoformat(checkpoint["ts"]),
                "parent_ts": datetime.fromisoformat(checkpoint.get("parent_ts"))
                if checkpoint.get("parent_ts")
                else None,
                "checkpoint": pickle.dumps(checkpoint),
                # "metadata": metadata,
            }

            conn.execute(self.checkpoints.insert(), record)
            conn.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "thread_ts": checkpoint["ts"],
                "workspace_id": workspace_id,
            }
        }
