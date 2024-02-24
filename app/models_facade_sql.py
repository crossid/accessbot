import logging
from typing import Optional

import sqlalchemy
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Table,
)
from sqlalchemy.engine import Engine

from app.id import generate
from app.models import AccessRequest, ChatMessage, Org
from app.models_facade import (
    ChatMessageFacade,
    OrgFacade,
    RequestFacade,
    TransactionContext,
)

metadata = MetaData()

ORG_TABLE_NAME = "org"
REQUEST_TABLE_NAME = "request"

org_table = sqlalchemy.Table(
    ORG_TABLE_NAME,
    metadata,
    Column("id", String(10), primary_key=True),
    Column("display_name", String(32), nullable=False),
    Column("external_id", String(10), nullable=True),
    Column("config", JSON(), nullable=False),
    Column("creator_id", String(32), nullable=False),
)


request_table = sqlalchemy.Table(
    REQUEST_TABLE_NAME,
    metadata,
    Column("id", String(10), primary_key=True),
    Column("org_id", String(10), ForeignKey(org_table.c.id), nullable=True),
    Column("owner_id", String(32), nullable=False),
    Column("status", String(32), nullable=False),
    Column("external_id", String(10), nullable=True),
    Column("context", JSON(), nullable=False),
    Column("created_at", DateTime(), nullable=False),
)


class OrgFacadeSQL(OrgFacade):
    default_table_name: str = ORG_TABLE_NAME
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
        query = self.orgs.select().where(self.orgs.c.id == org_id).limit(1)
        result: object = tx_context.connection.execute(query).first()
        if result:
            return Org(**result._asdict())

    def insert(self, org: Org, tx_context: TransactionContext) -> Org:
        if org.id is None:
            org.id = generate()
        o = org.model_dump()
        tx_context.connection.execute(self.orgs.insert(), o)
        return org


MESSAGE_TABLE_NAME = "message"


class RequestFacadeSQL(RequestFacade):
    default_requests_table_name: str = REQUEST_TABLE_NAME
    default_messages_table_name: str = MESSAGE_TABLE_NAME
    metadata: MetaData
    requests: Table
    messages: Table

    @classmethod
    def build_request_table(cls, metadata: MetaData, table_name: str) -> Table:
        return request_table

    def __init__(
        self,
        requests_table_name: str = default_requests_table_name,
        messages_table_name: str = default_messages_table_name,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.metadata = metadata
        self.requests = self.build_request_table(
            metadata=self.metadata, table_name=requests_table_name
        )
        self._logger = logger

    def create_tables(self, engine: Engine):
        self.metadata.create_all(engine)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def get_by_id(
        self, id: str, tx_context: TransactionContext
    ) -> Optional[AccessRequest]:
        query = self.requests.select().where(self.requests.c.id == id).limit(1)
        result: object = tx_context.connection.execute(query).first()
        if result:
            return AccessRequest(**result._asdict())

    def insert(
        self, req: AccessRequest, tx_context: TransactionContext
    ) -> AccessRequest:
        if req.id is None:
            req.id = generate()
        o = req.model_dump()
        tx_context.connection.execute(self.requests.insert(), o)
        return req


class ChatMessageFacadeSQL(ChatMessageFacade):
    default_table_name: str = MESSAGE_TABLE_NAME
    metadata: MetaData
    messages: Table

    @classmethod
    def build_table(
        cls, metadata: MetaData, table_name: str, request_table: Table
    ) -> Table:
        return sqlalchemy.Table(
            table_name,
            metadata,
            Column("id", String(10), primary_key=True),
            Column(
                "conversation_id",
                String(10),
                # ForeignKey(request_table.c.id),
                nullable=False,
            ),
            Column("type", String(32), nullable=False),
            Column("content", String(1024), nullable=True),
            Column("created_at", DateTime(), nullable=False),
        )

    def __init__(
        self,
        messages_table_name: str = default_table_name,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.metadata = metadata
        self.messages = self.build_table(
            metadata=self.metadata,
            table_name=messages_table_name,
            request_table=request_table,
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
