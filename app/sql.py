import logging
from contextlib import contextmanager

from sqlalchemy import create_engine

from .models_facade_sql import ChatMessageFacadeSQL, ConversationStoreSQL, OrgFacadeSQL
from .settings import settings
from .tx import TransactionContext

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT = 10

sqlalchemy_engine = create_engine(
    settings.DB_URI,
    echo=True,
    # connect_args={"connect_timeout": 10},
)
org_facade = OrgFacadeSQL()
conversation_store = ConversationStoreSQL()
message_facade = ChatMessageFacadeSQL()


def create_tables():
    org_facade.create_tables(sqlalchemy_engine)
    conversation_store.create_tables(sqlalchemy_engine)
    message_facade.create_tables(sqlalchemy_engine)
    pass


class SQLAlchemyTransactionContext(TransactionContext):
    def __init__(self, engine=None):
        if engine is not None:
            self.engine = engine
        else:
            self.engine = sqlalchemy_engine
        self.connection = None
        self.transaction = None

    def start(self):
        self.connection = self.engine.connect()
        self.transaction = self.connection.begin()

    def commit(self):
        if self.transaction and not self.transaction.is_active:
            return  # Avoid committing if the transaction is already deassociated
        self.transaction.commit()
        self.connection.close()
        logger.debug("commit: tx committed, conn closed")

    def rollback(self):
        if self.transaction and not self.transaction.is_active:
            return  # Avoid rolling back if the transaction is already deassociated

        self.transaction.rollback()
        self.connection.close()
        logger.debug("rollback: tx rollbacked, conn closed")

    @contextmanager
    def manage(self):
        try:
            self.start()
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise
        finally:
            if self.connection is not None:
                self.connection.close()
