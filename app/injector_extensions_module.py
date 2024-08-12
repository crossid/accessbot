from urllib.parse import parse_qs, urlparse

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
from .settings import settings
from .vault.api import VaultAPI
from .vault.env_vars import EnvVarVault


class ExtensionModule(injector.Module):
    @injector.provider
    def provide_vault(self) -> VaultAPI:
        parsed_url = urlparse(settings.VAULT_URI)
        protocol = parsed_url.scheme
        qp = parse_qs(parsed_url.query)
        if protocol == "env":
            return EnvVarVault()
        elif protocol == "k8s":
            from app.vault.k8s import KubernetesVaultImpl

            return KubernetesVaultImpl(
                namespace=parsed_url.netloc,
                config_file=qp.get("config_file", [None])[0],
            )
        else:
            raise ValueError(f"Unsupported vault protocol: {protocol}")

    def configure(self, binder):
        binder.bind(UserStore, to=UserStoreFromJsonFile, scope=injector.singleton)
        binder.bind(
            WorkspaceStoreHooks, to=WorkspaceStoreHooksPass, scope=injector.singleton
        )
        binder.bind(
            RegistrationProviderInterface,
            to=DefaultRegistrationProvider,
            scope=injector.singleton,
        )
