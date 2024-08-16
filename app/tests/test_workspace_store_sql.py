import pytest
from fastapi import HTTPException
from sqlalchemy.engine import create_engine

from app.id import generate
from app.models import Workspace
from app.models_stores import WorkspaceStoreHooks, WorkspaceStoreProxy
from app.models_stores_sql import WorkspaceStoreSQL
from app.sql import SQLAlchemyTransactionContext


@pytest.fixture(scope="class")
def db():
    engine = create_engine("sqlite:///:memory:")
    test_store = WorkspaceStoreSQL()
    test_store.create_tables(engine)
    return engine, test_store


@pytest.mark.usefixtures("db")
class TestWorkspaceStoreSQL:
    def test_insert_workspace(self, db):
        engine, test_store = db
        with SQLAlchemyTransactionContext(engine=engine).manage() as tx_context:
            ws = Workspace(
                display_name="Acme, Inc.",
                name="acme",
                created_by=generate(),
                config={},
            )
            pws = test_store.insert(
                ws, tx_context=tx_context, current_user=None, background_tasks=None
            )
            assert pws is not None
            assert pws.id is not None
            lws = test_store.get_by_id(pws.id, tx_context=tx_context)
            assert lws is not None
            assert lws.id == pws.id
            assert lws.display_name == "Acme, Inc."

    def test_insert_workspace_dup(self, db):
        engine, test_store = db
        with SQLAlchemyTransactionContext(engine=engine).manage() as tx_context:
            ws = Workspace(
                display_name="Acme, Inc.",
                name="acme",
                created_by=generate(),
                config={},
            )
            with pytest.raises(HTTPException) as exc_info:
                test_store.insert(
                    ws, tx_context=tx_context, current_user=None, background_tasks=None
                )
            assert exc_info.value.status_code == 409

    def test_insert_workspace_with_hook(self, db):
        engine, test_store = db

        class WorkspaceHooks(WorkspaceStoreHooks):
            def pre_insert(self, workspace, tx_context, current_user, background_tasks):
                workspace.display_name = workspace.display_name.upper()

            def pre_delete(self, workspace, tx_context, current_user, background_tasks):
                pass

            def post_delete(
                self, workspace, tx_context, current_user, background_tasks
            ):
                pass

        f = WorkspaceStoreProxy(store=test_store, hooks=WorkspaceHooks())
        with SQLAlchemyTransactionContext(engine=engine).manage() as tx_context:
            ws = Workspace(
                display_name="Acme1, Inc.",
                name="acme1",
                created_by=generate(),
                config={},
            )
            f.insert(
                ws, tx_context=tx_context, current_user=None, background_tasks=None
            )
            lws = test_store.get_by_id(ws.id, tx_context=tx_context)
            assert lws.name == "acme1"
            assert lws.display_name == "ACME1, INC."

    def test_get_by_id_not_found(self, db):
        engine, test_store = db
        with SQLAlchemyTransactionContext(engine=engine).manage() as tx_context:
            rws = test_store.get_by_id("non_existing_id", tx_context=tx_context)
            assert rws is None

    def test_tx(self, db):
        engine, test_store = db
        with SQLAlchemyTransactionContext(engine=engine).manage() as tx_context:
            ws = Workspace(
                display_name="Acme2, Inc.",
                name="acme2",
                created_by=generate(),
                config={},
            )
            test_store.insert(
                ws, tx_context=tx_context, current_user=None, background_tasks=None
            )
            tx_context.rollback()
        with SQLAlchemyTransactionContext(engine=engine).manage() as tx_context:
            rws = test_store.get_by_id(ws.id, tx_context=tx_context)
            assert rws is None
