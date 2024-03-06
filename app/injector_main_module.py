import injector

from .models_facade import (
    ChatMessageFacade,
    ConversationStore,
    OrgFacade,
    OrgFacadeHooks,
    OrgFacadeProxy,
)
from .models_facade_sql import (
    ChatMessageFacadeSQL,
    ConversationStoreSQL,
    OrgFacadeSQL,
)


class MainModule(injector.Module):
    @injector.provider
    def provide_org_facade(
        self, hooks: injector.Optional[OrgFacadeHooks] = None
    ) -> OrgFacade:
        org_facade_sql = OrgFacadeSQL()
        return OrgFacadeProxy(facade=org_facade_sql, hooks=hooks)

    def configure(self, binder):
        # binder.bind(UserStore, to=UserStoreSCIM, scope=injector.singleton)
        binder.bind(
            ConversationStore, to=ConversationStoreSQL, scope=injector.singleton
        )
        binder.bind(
            ChatMessageFacade, to=ChatMessageFacadeSQL, scope=injector.singleton
        )
