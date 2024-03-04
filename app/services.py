import importlib

from .models_facade import OrgFacadeHooks, OrgFacadeProxy
from .models_facade_sql import ChatMessageFacadeSQL, OrgFacadeSQL, RequestFacadeSQL
from .settings import settings


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


def factory_request_db_facade():
    return RequestFacadeSQL()


def factory_message_db_facade():
    return ChatMessageFacadeSQL()
