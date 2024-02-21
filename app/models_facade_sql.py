import logging
from typing import Optional

import sqlalchemy
from sqlalchemy import (
    JSON,
    Column,
    MetaData,
    String,
    Table,
)
from sqlalchemy.engine import Engine

from app.id import generate
from app.models import Org
from app.models_facade import OrgFacade

ORG_TABLE_NAME = "org"


class OrgFacadeSQL(OrgFacade):
    default_table_name: str = ORG_TABLE_NAME
    engine: Engine
    metadata: MetaData
    orgs: Table

    @classmethod
    def build_table(cls, metadata: MetaData, table_name: str) -> Table:
        return sqlalchemy.Table(
            table_name,
            metadata,
            Column("id", String(10), primary_key=True),
            Column("display_name", String(32), nullable=False),
            Column("external_id", String(10), nullable=True),
            Column("config", JSON(), nullable=False),
            Column("creator_id", String(32), nullable=False),
        )

    def __init__(
        self,
        engine: Engine,
        table_name: str = default_table_name,
        logger: logging.Logger = logging.getLogger(__name__),
    ):
        self.metadata = sqlalchemy.MetaData()
        self.orgs = self.build_table(metadata=self.metadata, table_name=table_name)
        self._logger = logger
        self.engine = engine

    def create_tables(self):
        self.metadata.create_all(self.engine)

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    def get_by_id(self, org_id: str) -> Optional[Org]:
        query = self.orgs.select().where(self.orgs.c.id == org_id).limit(1)
        with self.engine.connect() as conn:
            result: object = conn.execute(query).first()
            if result:
                return Org(**result._asdict())

    def insert(self, org: Org) -> Org:
        with self.engine.begin() as conn:
            if org.id is None:
                org.id = generate()
            o = org.model_dump()
            conn.execute(self.orgs.insert(), o)
            return org
