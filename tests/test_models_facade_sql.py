import unittest

from sqlalchemy.engine import create_engine

from app.id import generate
from app.models import Org
from app.models_facade import OrgFacadeHooks, OrgFacadeProxy
from app.models_facade_sql import OrgFacadeSQL


class TestOrgFacadeSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Set up a test engine, possibly an in-memory database
        cls.engine = create_engine("sqlite:///:memory:")
        cls.test_facade = OrgFacadeSQL(engine=cls.engine)
        cls.test_facade.create_tables()

    def test_insert_org(self):
        org = Org(display_name="Acme, Inc.", creator_id=generate(), config={})
        porg = self.test_facade.insert(org)
        self.assertIsNotNone(porg)
        self.assertIsNotNone(porg.id)
        # Retrieve the org to verify it was inserted correctly
        lorg = self.test_facade.get_by_id(porg.id)
        self.assertIsNotNone(lorg)
        self.assertEqual(lorg.id, porg.id)
        self.assertEqual(lorg.display_name, "Acme, Inc.")

    def test_insert_org_with_hook(self):
        class OrgHooks(OrgFacadeHooks):
            def pre_insert(self, org: "Org"):
                org.display_name = org.display_name.upper()

        f = OrgFacadeProxy(facade=self.test_facade, hooks=OrgHooks())

        org = Org(display_name="Acme, Inc.", creator_id=generate(), config={})
        f.insert(org)
        lorg = self.test_facade.get_by_id(org.id)
        self.assertEqual("ACME, INC.", lorg.display_name)

    def test_get_by_id_not_found(self):
        retrieved_org = self.test_facade.get_by_id("non_existing_id")
        self.assertIsNone(retrieved_org)


if __name__ == "__main__":
    unittest.main()
