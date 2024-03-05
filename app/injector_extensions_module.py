import injector

from app.models_facade import OrgFacadeHooks, OrgFacadeHooksPass, UserStore
from app.user_store_scim import UserStoreSCIM
from app.vault import VaultAPI
from app.vault_env_vars import EnvVarVault


class ExtensionModule(injector.Module):
    def configure(self, binder):
        binder.bind(UserStore, to=UserStoreSCIM, scope=injector.singleton)
        binder.bind(OrgFacadeHooks, to=OrgFacadeHooksPass, scope=injector.singleton)
        binder.bind(VaultAPI, to=EnvVarVault, scope=injector.singleton)
