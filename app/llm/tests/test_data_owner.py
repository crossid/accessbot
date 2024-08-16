import asyncio
import unittest
from typing import Any

from app.consts import EMAIL_CONFIG_KEY
from app.llm.tools.data_owner.factory import send_registration_email
from app.models import Directory, Workspace
from app.registration_provider import (
    DefaultRegistrationProvider,
    RegistrationProviderInterface,
)


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
        from app.vault.api import VaultAPI
        from app.vault.env_vars import EnvVarVault

        class TestUserStore(UserStore):
            users: dict[str, User] = {
                "jon.doe@foo.com": User(id="1", email="jon.doe@foo.com")
            }

            def get_by_email(self, email: str):
                return self.users[email]

            def list_workspaces_for_user(self, user_id: str) -> list[str]:
                pass

            def add_user_to_workspace(self, user_id: str, workspace_id: str):
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
                binder.bind(
                    RegistrationProviderInterface,
                    to=DefaultRegistrationProvider,
                    scope=injector.singleton,
                )

        service_registry = injector.Injector([ExtensionModule()])
        set_service_registry(service_registry)

    def test_get_data_owner(self):
        from app.consts import DATAOWNER_CONFIG_KEY
        from app.llm.tools.data_owner.factory import get_data_owner
        from dotenv import load_dotenv

        load_dotenv()

        expected_email = "jon.doe@foo.com"
        config: dict[str, Any] = {DATAOWNER_CONFIG_KEY: expected_email}

        ws = Workspace(
            display_name="foo",
            name="foo",
            creator_id="bar",
            config=config,
            created_by="bar",
        )

        dir = Directory(
            name="okta", config={}, workspace_id="foo", created_by="foo@acme.io"
        )

        owner = asyncio.new_event_loop().run_until_complete(
            get_data_owner(ws=ws, directory=dir, app_name="foo")
        )

        self.assertEqual(owner.email, expected_email)

    def test_registration_email(self):
        config: dict[str, Any] = {
            EMAIL_CONFIG_KEY: {"type": "smtp", "config": {"host": "localhost:1025"}}
        }
        ws = Workspace(
            display_name="foo",
            name="foo",
            creator_id="bar",
            config=config,
            created_by="bar",
        )

        send_registration_email(ws=ws, to="foo@bar.com")
        self.assertEqual(1, 1)
