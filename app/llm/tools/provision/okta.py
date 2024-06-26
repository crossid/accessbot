from .iface import ProvisionInterface


class OktaImpl(ProvisionInterface):
    def __init__(self, tenant, token) -> None:
        try:
            from okta.client import Client as OktaClient
        except ImportError:
            raise ImportError(
                "Could not import atlassian package. "
                "Please install it with `pip install okta`."
            )

        config = {"orgUrl": f"https://{tenant}", "token": token}
        self.client = OktaClient(config)

    async def approve_request(self, requester_email: str, **kwargs) -> bool:
        role_id = kwargs.get("role_id", None)
        if role_id is None:
            raise ValueError("role_id must be set for okta provisioning")
        users, _, err = await self.client.list_users(
            query_params={"search": f'email eq "{requester_email}"'}
        )

        if err is not None:
            raise ValueError(err.error_summary)

        if users is None or len(users) == 0:
            raise ValueError(f"could not find okta user for email: {requester_email}")

        oktaUser = users[0]

        _, err = await self.client.add_user_to_group(
            groupId=role_id, userId=oktaUser.id
        )

        if err is not None:
            raise ValueError(err.error_summary)

        return True
