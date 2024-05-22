import asyncio
import unittest
from typing import Any

from app.models import Workspace


class TestGetDataOwner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import injector

        from app.models import User
        from app.models_stores import (
            UserStore,
            WorkspaceStoreHooks,
            WorkspaceStoreHooksPass,
        )
        from app.services import set_service_registry
        from app.vault import VaultAPI
        from app.vault_env_vars import EnvVarVault

        class TestUserStore(UserStore):
            users: dict[str, User] = {
                "jon.doe@foo.com": User(id="1", email="jon.doe@foo.com")
            }

            def get_by_email(self, email: str):
                return self.users[email]

            def list_workspaces_for_user(self, user_id: str) -> list[str]:
                pass

        class ExtensionModule(injector.Module):
            def configure(self, binder):
                binder.bind(UserStore, to=TestUserStore, scope=injector.singleton)
                binder.bind(
                    WorkspaceStoreHooks,
                    to=WorkspaceStoreHooksPass,
                    scope=injector.singleton,
                )
                binder.bind(VaultAPI, to=EnvVarVault, scope=injector.singleton)

        service_registry = injector.Injector([ExtensionModule()])
        set_service_registry(service_registry)

    def test_get_data_owner(self):
        from dotenv import load_dotenv

        from app.llm.tools.consts import DATAOWNER_CONFIG_KEY
        from app.llm.tools.data_owner.factory import get_data_owner

        load_dotenv()

        expected_email = "jon.doe@foo.com"
        config: dict[str, Any] = {
            DATAOWNER_CONFIG_KEY: {"default_data_owner_email": expected_email}
        }

        ws = Workspace(
            display_name="foo", creator_id="bar", config=config, created_by="bar"
        )

        owner = asyncio.new_event_loop().run_until_complete(
            get_data_owner(ws=ws, app_name="foo", directory="okta")
        )

        self.assertEqual(owner.email, expected_email)
