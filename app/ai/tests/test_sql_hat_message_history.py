import logging.config
import unittest
from unittest import TestCase

import yaml
from sqlalchemy import create_engine

from app.ai.messages import get_chat_msg_history
from app.models_facade_sql import ChatMessageFacadeSQL
from app.sql import SQLAlchemyTransactionContext


class TestMessages(TestCase):
    @classmethod
    def setUpClass(cls):
        with open("log_conf.yml", "r") as f:
            config = yaml.safe_load(f)
            logging.config.dictConfig(config)

        # Set up a test engine, possibly an in-memory database
        cls.engine = create_engine("sqlite:///:memory:")
        cls.test_facade = ChatMessageFacadeSQL()
        cls.test_facade.create_tables(cls.engine)

    def test_get_chat_msg_history(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            self.test_facade.list(filter="foo", tx_context=tx_context)
            h = get_chat_msg_history(
                conversation_id="foo", engine=self.engine, facade=self.test_facade
            )
            self.assertEqual(len(h.messages), 0)
            h.add_user_message("hi there")
            self.assertEqual(len(h.messages), 1)
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            h = get_chat_msg_history(
                conversation_id="foo", engine=self.engine, facade=self.test_facade
            )
            self.assertEqual(len(h.messages), 1)
            h.clear()
            self.assertEqual(len(h.messages), 0)


if __name__ == "__main__":
    unittest.main()
