import injector

from .models_stores import UserStore, WorkspaceStoreHooks, WorkspaceStoreHooksPass
from .user_store_scim import UserStoreSCIM
from .vault import VaultAPI
from .vault_env_vars import EnvVarVault


class ExtensionModule(injector.Module):
    def configure(self, binder):
        binder.bind(UserStore, to=UserStoreSCIM, scope=injector.singleton)
        binder.bind(
            WorkspaceStoreHooks, to=WorkspaceStoreHooksPass, scope=injector.singleton
        )
        binder.bind(VaultAPI, to=EnvVarVault, scope=injector.singleton)
