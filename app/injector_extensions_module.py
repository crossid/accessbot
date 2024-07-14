import injector

from app.registration_provider import (
    DefaultRegistrationProvider,
    RegistrationProviderInterface,
)

from .json_file_stores import UserStoreFromJsonFile
from .models_stores import (
    UserStore,
    WorkspaceStoreHooks,
    WorkspaceStoreHooksPass,
)
from .vault import VaultAPI
from .vault_env_vars import EnvVarVault


class ExtensionModule(injector.Module):
    def configure(self, binder):
        binder.bind(UserStore, to=UserStoreFromJsonFile, scope=injector.singleton)
        binder.bind(
            WorkspaceStoreHooks, to=WorkspaceStoreHooksPass, scope=injector.singleton
        )
        binder.bind(VaultAPI, to=EnvVarVault, scope=injector.singleton)
        binder.bind(
            RegistrationProviderInterface,
            to=DefaultRegistrationProvider,
            scope=injector.singleton,
        )
