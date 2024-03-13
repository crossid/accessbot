import unittest

from sqlalchemy.engine import create_engine

from app.id import generate
from app.models import Workspace
from app.models_stores import WorkspaceStoreHooks, WorkspaceStoreProxy
from app.models_stores_sql import WorkspaceStoreSQL
from app.sql import SQLAlchemyTransactionContext
from app.tx import TransactionContext


class TestWorkspaceStoreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # with open("log_conf.yml", "r") as f:
        #     config = yaml.safe_load(f)
        #     logging.config.dictConfig(config)

        # Set up a test engine, possibly an in-memory database
        cls.engine = create_engine("sqlite:///:memory:")
        cls.test_store = WorkspaceStoreSQL()
        cls.test_store.create_tables(cls.engine)

    def test_insert_workspace(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            ws = Workspace(display_name="Acme, Inc.", created_by=generate(), config={})
            pws = self.test_store.insert(ws, tx_context=tx_context)
            self.assertIsNotNone(pws)
            self.assertIsNotNone(pws.id)
            # # Retrieve the ws to verify it was inserted correctly
            lws = self.test_store.get_by_id(pws.id, tx_context=tx_context)
            self.assertIsNotNone(lws)
            self.assertEqual(lws.id, pws.id)
            self.assertEqual(lws.display_name, "Acme, Inc.")

    def test_insert_workspace_with_hook(self):
        class WorkspaceHooks(WorkspaceStoreHooks):
            def pre_insert(self, workspace: Workspace, tx_context: TransactionContext):
                workspace.display_name = workspace.display_name.upper()

            def pre_delete(self, workspace: Workspace, tx_context: TransactionContext):
                pass

        f = WorkspaceStoreProxy(store=self.test_store, hooks=WorkspaceHooks())

        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            ws = Workspace(display_name="Acme, Inc.", created_by=generate(), config={})
            f.insert(ws, tx_context=tx_context)
            lws = self.test_store.get_by_id(ws.id, tx_context=tx_context)
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            lws = self.test_store.get_by_id(ws.id, tx_context=tx_context)
            self.assertEqual("ACME, INC.", lws.display_name)

    def test_get_by_id_not_found(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            rws = self.test_store.get_by_id("non_existing_id", tx_context=tx_context)
            self.assertIsNone(rws)

    def test_tx(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            ws = Workspace(display_name="Acme, Inc.", created_by=generate(), config={})
            self.test_store.insert(ws, tx_context=tx_context)
            tx_context.rollback()
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            rws = self.test_store.get_by_id("non_existing_id", tx_context=tx_context)
            self.assertIsNone(rws)


if __name__ == "__main__":
    unittest.main()
