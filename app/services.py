from typing import List

import injector
from fastapi import Query

from .models_stores import (
    ApplicationStore,
    ChatMessageStore,
    CheckpointStore,
    ConversationStore,
    DirectoryStore,
    UserStore,
    WorkspaceStore,
)
from .vault import VaultAPI

_service_registry: injector.Injector = None


def service_registry() -> injector.Injector:
    global _service_registry
    return _service_registry


def set_service_registry(injector: injector.Injector):
    global _service_registry
    _service_registry = injector


def get_service(service_class: type) -> callable:
    """
    Define a route using the dependency
    example:
        @app.get("/")
        async def list(service: MyService = Depends(get_service(MyService))):

    Args:
        service_class (type): The class of the service to be resolved.

    Returns:
        callable: A function that resolves the dependency and returns an instance of the service class.
    """

    def dependency() -> object:
        return service_registry().get(service_class)

    return dependency


def factory_ws_store():
    return service_registry().get(WorkspaceStore)


def factory_dir_store():
    return service_registry().get(DirectoryStore)


def factory_user_store():
    return service_registry().get(UserStore)


def factory_conversation_store():
    return service_registry().get(ConversationStore)


def factory_message_store():
    return service_registry().get(ChatMessageStore)


def factory_checkpointer():
    return service_registry().get(CheckpointStore)


def factory_app_store():
    return service_registry().get(ApplicationStore)


def factory_vault():
    return service_registry().get(VaultAPI)


async def pagination_params(
    q: str | None = None,
    offset: int = 0,
    limit: int = 10,
    projection: List[str] = Query([]),
):
    return {"q": q, "offset": offset, "limit": limit, "projection": projection}
