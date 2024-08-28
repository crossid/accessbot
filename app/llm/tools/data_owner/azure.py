from app.utils.azure_client import get_azure_client, get_users_by_filter

from .iface import DataOwnerInterface


class AzureImpl(DataOwnerInterface):
    attribute_name: str

    def __init__(
        self,
        attribute_name="customSecurityAttributes/DataOwnership/dataOwner",
    ) -> None:
        self.client = get_azure_client()
        self.attribute_name = attribute_name

    async def get_data_owner(self, app_name: str, **kwargs) -> str:
        select = ["id", "displayName", "mail"]
        filter = f"{self.attribute_name} eq '{app_name}'"

        users = await get_users_by_filter(
            filter=filter, select=select, client=self.client
        )
        if len(users.value) == 0:
            raise ValueError(f"No data owners found for app {app_name}")

        data_owner = users.value[0]
        if data_owner.mail is None:
            raise ValueError("No email on Azure data owner")

        return data_owner.mail
