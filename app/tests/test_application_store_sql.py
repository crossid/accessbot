import pytest
from sqlalchemy.engine import create_engine

from app.models import Application
from app.models_stores_sql import ApplicationStoreSQL
from app.sql import SQLAlchemyTransactionContext


@pytest.fixture(scope="class")
def setup_database(request):
    # Set up a test engine, possibly an in-memory database
    engine = create_engine("sqlite:///:memory:")
    test_store = ApplicationStoreSQL()
    test_store.create_tables(engine)

    # Assign the engine and test_store to the test class
    request.cls.engine = engine
    request.cls.test_store = test_store
    yield  # yield here if needed, but typically you might yield the engine/test_store for other uses.


@pytest.mark.usefixtures("setup_database")
class TestWorkspaceStoreSQL:
    def test_insert_workspace(self):
        with SQLAlchemyTransactionContext(engine=self.engine).manage() as tx_context:
            app = Application(
                id="1",
                workspace_id="1",
                display_name="FooQuery",
                name="fooquery",
                aliases=["fquery", "fq"],
                extra_instructions="dssa",
                provision_schema=None,
            )
            pws = self.test_store.insert(app, tx_context=tx_context)
            assert pws is not None
            assert pws.id is not None
            # Retrieve the ws to verify it was inserted correctly
            lws = self.test_store.get_by_id(pws.id, "1", tx_context=tx_context)
            assert lws is not None
            assert lws.id == pws.id

            lws = self.test_store.get_by_name("fooquery", "1", tx_context=tx_context)
            assert lws is not None
            assert lws.id == pws.id

            lws = self.test_store.get_by_name("fquery", "1", tx_context=tx_context)
            assert lws is not None
            assert lws.id == pws.id
