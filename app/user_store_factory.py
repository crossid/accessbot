from .classes import instantiate_class
from .models_facade import UserStore
from .settings import settings


def create_user_store(fqdn_class=settings.USER_STORE_CLASS) -> UserStore:
    store = instantiate_class(fqdn_class)
    return store
