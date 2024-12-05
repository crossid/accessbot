import pytest

from app.services import set_service_registry
from app.user_stores.user_store_azure import AzureUserStore


@pytest.mark.skip(
    reason="This is an integration test and will not work without connection to azure beforehand"
)
class TestAzureUserStore:
    @pytest.fixture(autouse=True)
    def setup(self):
        import injector
        from azure.core.credentials import TokenCredential
        from azure.identity import DefaultAzureCredential

        class ExtensionModule(injector.Module):
            @injector.provider
            def provide_azure_credentials(self) -> TokenCredential:
                return DefaultAzureCredential()

        service_registry = injector.Injector([ExtensionModule()])
        set_service_registry(service_registry)
        self.store = AzureUserStore()

    def test_get_by_email(self):
        expected_email = "jon.doe@foo.io"
        user = self.store.get_by_email(expected_email)
        assert user is not None, "user should exist"
        assert user.email == expected_email

    def test_list_workspaces(self):
        workspaces = self.store.list_workspaces_for_user("jon.doe@foo.io")
        assert len(workspaces) > 0, "user should have at least 1 org"
