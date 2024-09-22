from app.utils.azure_client import get_azure_client, get_users_by_filter

from .iface import ProvisionInterface


class AzureImpl(ProvisionInterface):
    def __init__(self) -> None:
        self.client = get_azure_client()

    async def approve_request(self, requester_email: str, **kwargs) -> bool:
        from msgraph.generated.models.reference_create import ReferenceCreate

        role_id = kwargs.get("role_id", None)
        if role_id is None:
            raise ValueError("role_id must be set for Azure provisioning")

        users = await get_users_by_filter(
            filter=f"mail eq '{requester_email}'", select=["id"], client=self.client
        )

        if len(users.value) == 0:
            raise ValueError(f"Could not find Azure user for email: {requester_email}")

        user_id = users.value[0].id

        request_body = ReferenceCreate(
            odata_id=f"https://graph.microsoft.com/v1.0/directoryObjects/{user_id}",
        )

        try:
            await self.client.groups.by_group_id(role_id).members.ref.post(request_body)
        except Exception as e:
            raise ValueError(f"Failed to add user to group: {str(e)}")

        return True
