import unittest

from sqlalchemy.engine import create_engine

from app.id import generate
from app.models import Org
from app.models_stores import OrgStoreHooks, OrgStoreProxy
from app.models_stores_sql import OrgStoreSQL
from app.sql import SQLAlchemyTransactionContext
from app.tx import TransactionContext


class TestOrgStoreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # with open("log_conf.yml", "r") as f:
        #     config = yaml.safe_load(f)
        #     logging.config.dictConfig(config)

        # Set up a test engine, possibly an in-memory database
        cls.engine = create_engine("sqlite:///:memory:")
        cls.test_store = OrgStoreSQL()
        cls.test_store.create_tables(cls.engine)

    def test_insert_org(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            org = Org(display_name="Acme, Inc.", creator_id=generate(), config={})
            porg = self.test_store.insert(org, tx_context=tx_context)
            self.assertIsNotNone(porg)
            self.assertIsNotNone(porg.id)
            # # Retrieve the org to verify it was inserted correctly
            lorg = self.test_store.get_by_id(porg.id, tx_context=tx_context)
            self.assertIsNotNone(lorg)
            self.assertEqual(lorg.id, porg.id)
            self.assertEqual(lorg.display_name, "Acme, Inc.")

    def test_insert_org_with_hook(self):
        class OrgHooks(OrgStoreHooks):
            def pre_insert(self, org: Org, tx_context: TransactionContext):
                org.display_name = org.display_name.upper()

            def pre_delete(self, org: Org, tx_context: TransactionContext):
                pass

        f = OrgStoreProxy(store=self.test_store, hooks=OrgHooks())

        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            org = Org(display_name="Acme, Inc.", creator_id=generate(), config={})
            f.insert(org, tx_context=tx_context)
            lorg = self.test_store.get_by_id(org.id, tx_context=tx_context)
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            lorg = self.test_store.get_by_id(org.id, tx_context=tx_context)
            self.assertEqual("ACME, INC.", lorg.display_name)

    def test_get_by_id_not_found(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            retrieved_org = self.test_store.get_by_id(
                "non_existing_id", tx_context=tx_context
            )
            self.assertIsNone(retrieved_org)

    def test_tx(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            org = Org(display_name="Acme, Inc.", creator_id=generate(), config={})
            self.test_store.insert(org, tx_context=tx_context)
            tx_context.rollback()
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            rorg = self.test_store.get_by_id("non_existing_id", tx_context=tx_context)
            self.assertIsNone(rorg)


if __name__ == "__main__":
    unittest.main()