import unittest
from unittest import TestCase

from app.llm.sql_chat_message_history import LangchainChatMessageHistory
from app.models_stores_sql import ChatMessageStoreSQL
from app.sql import SQLAlchemyTransactionContext
from sqlalchemy import create_engine


class TestMessages(TestCase):
    @classmethod
    def setUpClass(cls):
        # with open("log_conf.yml", "r") as f:
        #     config = yaml.safe_load(f)
        #     logging.config.dictConfig(config)

        # Set up a test engine, possibly an in-memory database
        cls.engine = create_engine("sqlite:///:memory:")
        cls.test_store = ChatMessageStoreSQL()
        cls.test_store.create_tables(cls.engine)

    def test_get_chat_msg_history(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            self.test_store.list(filter="foo", tx_context=tx_context)
            h = LangchainChatMessageHistory(
                conversation_id="foo",
                workspace_id="bar",
                store=self.test_store,
                tx_context=tx_context,
            )
            self.assertEqual(len(h.messages), 0)
            h.add_user_message("hi there")
            self.assertEqual(len(h.messages), 1)
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            h = LangchainChatMessageHistory(
                conversation_id="foo",
                workspace_id="bar",
                store=self.test_store,
                tx_context=tx_context,
            )
            self.assertEqual(len(h.messages), 1)
            h.clear()
            self.assertEqual(len(h.messages), 0)


if __name__ == "__main__":
    unittest.main()
