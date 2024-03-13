from app.models import User
from app.services import factory_user_store

from .iface import DataOwnerInterface


class OktaImpl(DataOwnerInterface):
    attribute_name: str

    def __init__(self, tenant, password, attribute_name="dataOwner") -> None:
        try:
            from okta.client import Client as OktaClient
        except ImportError:
            raise ImportError(
                "Could not import atlassian package. "
                "Please install it with `pip install okta`."
            )

        config = {"orgUrl": f"https://{tenant}", "token": password}
        self.client = OktaClient(config)
        self.attribute_name = attribute_name

    async def get_data_owner(self, rolename: str) -> User:
        role_id = rolename.split("/")[1]
        okta_group, _, err = await self.client.get_group(role_id)
        if err is not None:
            raise ValueError(err.error_summary)

        okta_data_owner = okta_group.profile.as_dict()[self.attribute_name]
        if okta_data_owner is None:
            return None

        oktaUser, _, err = await self.client.get_user(userId=okta_data_owner)
        if err is not None:
            raise ValueError(err.error_summary)

        if oktaUser.profile.email is None:
            raise ValueError("no email on okta user")

        user_store = factory_user_store()
        return user_store.get_by_email(email=oktaUser.profile.email)
