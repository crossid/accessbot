import unittest

from sqlalchemy import create_engine

from app.id import generate
from app.models import User
from app.models_facade_sql import UserStoreSQL
from app.sql import SQLAlchemyTransactionContext


class TestUserStoreSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        cls.test_facade = UserStoreSQL()
        cls.test_facade.create_tables(cls.engine)

    def test_crud(self):
        u = User(id=generate(), email="john@acme.io", name="John Doe")
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            u = self.test_facade.insert(u, tx_context=tx_context)
            lu = self.test_facade.get_by_id(u.id, tx_context=tx_context)
            self.assertDictEqual(u.model_dump(), lu.model_dump())
            # get by email
            u = self.test_facade.get_by_email("john@acme.io", tx_context=tx_context)
            self.assertIsNotNone(u)
