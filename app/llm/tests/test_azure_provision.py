import pytest

from app.llm.tools.provision.azure import AzureImpl
from app.services import set_service_registry


@pytest.mark.skip(
    reason="This is an integration test and will not work without connection to azure beforehand"
)
class TestAzureProvision:
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
        self.store = AzureImpl()

    def test_approve_request(self):
        user_email = "erez@crossid.io"
        role_id = "c2b6d634-06f4-4894-bcdd-50c51df50d85"
        approved = self.store.approve_request(
            requester_email=user_email, role_id=role_id
        )
        assert approved, "request should be approved"
