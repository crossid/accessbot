import unittest

from sqlalchemy.engine import create_engine

from app.models import Application
from app.models_stores_sql import ApplicationStoreSQL
from app.sql import SQLAlchemyTransactionContext


class TestWorkspaceStoreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up a test engine, possibly an in-memory database
        cls.engine = create_engine("sqlite:///:memory:")
        cls.test_store = ApplicationStoreSQL()
        cls.test_store.create_tables(cls.engine)

    def test_insert_workspace(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            app = Application(
                id="1",
                workspace_id="1",
                display_name="FooQuery",
                aliases=["fquery", "fq"],
                extra_instructions="dssa",
            )
            pws = self.test_store.insert(app, tx_context=tx_context)
            self.assertIsNotNone(pws)
            self.assertIsNotNone(pws.id)
            # # Retrieve the ws to verify it was inserted correctly
            lws = self.test_store.get_by_id(pws.id, "1", tx_context=tx_context)
            self.assertIsNotNone(lws)
            self.assertEqual(lws.id, pws.id)

            lws = self.test_store.get_by_name("fooquery", "1", tx_context=tx_context)
            self.assertIsNotNone(lws)
            self.assertEqual(lws.id, pws.id)

            lws = self.test_store.get_by_name("fquery", "1", tx_context=tx_context)
            self.assertIsNotNone(lws)
            self.assertEqual(lws.id, pws.id)


if __name__ == "__main__":
    unittest.main()
