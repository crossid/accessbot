import injector

from .models_stores import (
    ChatMessageStore,
    ConversationStore,
    WorkspaceStore,
    WorkspaceStoreHooks,
    WorkspaceStoreProxy,
)
from .models_stores_sql import (
    ChatMessageStoreSQL,
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

    def configure(self, binder):
        # binder.bind(UserStore, to=UserStoreSCIM, scope=injector.singleton)
        binder.bind(
            ConversationStore, to=ConversationStoreSQL, scope=injector.singleton
        )
        binder.bind(ChatMessageStore, to=ChatMessageStoreSQL, scope=injector.singleton)
