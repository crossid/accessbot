import injector
from langgraph.checkpoint import BaseCheckpointSaver

from app.sql import sqlalchemy_engine

from .models_stores import (
    ApplicationStore,
    ChatMessageStore,
    ConversationStore,
    WorkspaceStore,
    WorkspaceStoreHooks,
    WorkspaceStoreProxy,
)
from .models_stores_sql import (
    ApplicationStoreSQL,
    ChatMessageStoreSQL,
    CheckpointStoreSQL,
    ConversationStoreSQL,
    WorkspaceStoreSQL,
)


class MainModule(injector.Module):
    @injector.provider
    def provide_workspace_store(
        self, hooks: injector.Optional[WorkspaceStoreHooks] = None
    ) -> WorkspaceStore:
        workspace_store_sql = WorkspaceStoreSQL()
        return WorkspaceStoreProxy(store=workspace_store_sql, hooks=hooks)

    @injector.provider
    def provide_checkpoint_store(self) -> BaseCheckpointSaver:
        checkpoint_store_sql = CheckpointStoreSQL(engine=sqlalchemy_engine)
        return checkpoint_store_sql

    def configure(self, binder):
        # binder.bind(UserStore, to=UserStoreSCIM, scope=injector.singleton)
        binder.bind(
            ConversationStore, to=ConversationStoreSQL, scope=injector.singleton
        )
        binder.bind(ChatMessageStore, to=ChatMessageStoreSQL, scope=injector.singleton)
        binder.bind(ApplicationStore, to=ApplicationStoreSQL, scope=injector.singleton)
