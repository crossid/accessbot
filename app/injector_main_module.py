import injector

from .models_stores import (
    ChatMessageStore,
    ConversationStore,
    OrgStore,
    OrgStoreHooks,
    OrgStoreProxy,
)
from .models_stores_sql import (
    ChatMessageStoreSQL,
    ConversationStoreSQL,
    OrgStoreSQL,
)


class MainModule(injector.Module):
    @injector.provider
    def provide_org_store(
        self, hooks: injector.Optional[OrgStoreHooks] = None
    ) -> OrgStore:
        org_store_sql = OrgStoreSQL()
        return OrgStoreProxy(store=org_store_sql, hooks=hooks)

    def configure(self, binder):
        # binder.bind(UserStore, to=UserStoreSCIM, scope=injector.singleton)
        binder.bind(
            ConversationStore, to=ConversationStoreSQL, scope=injector.singleton
        )
        binder.bind(ChatMessageStore, to=ChatMessageStoreSQL, scope=injector.singleton)
