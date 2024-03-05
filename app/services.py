import importlib

from .models_facade import OrgFacadeHooks, OrgFacadeProxy
from .models_facade_sql import ChatMessageFacadeSQL, ConversationStoreSQL, OrgFacadeSQL
from .settings import settings
from .user_store_factory import create_user_store


def factory_org_db_facade():
    hooks: OrgFacadeHooks = None
    if settings.ORG_FACADE_HOOKS:
        sp = settings.ORG_FACADE_HOOKS.split(":")
        if len(sp) == 2:
            hook_module_name = sp[0]
            hook_class_name = sp[1]
        if hook_module_name and hook_class_name:
            hook_module = importlib.import_module(hook_module_name)
            hook_class = getattr(hook_module, hook_class_name)
            hooks = hook_class()

    return OrgFacadeProxy(facade=OrgFacadeSQL(), hooks=hooks)


org_facade = factory_org_db_facade()
conversation_store = ConversationStoreSQL()
user_store = create_user_store()
message_facade = ChatMessageFacadeSQL()


def factory_conversation_db_facade():
    return conversation_store


def factory_message_db_facade():
    return message_facade
