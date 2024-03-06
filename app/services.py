import injector

from .models_facade import (
    ChatMessageFacade,
    ConversationStore,
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


def factory_conversation_db_facade():
    return service_registry().get(ConversationStore)


def factory_message_db_facade():
    return service_registry().get(ChatMessageFacade)


def factory_vault():
    return service_registry().get(VaultAPI)
