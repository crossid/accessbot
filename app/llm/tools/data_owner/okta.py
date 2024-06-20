from app.models import User
from app.services import factory_user_store

from .iface import DataOwnerInterface


class OktaImpl(DataOwnerInterface):
    attribute_name: str

    def __init__(self, tenant, token, attribute_name="data_owner") -> None:
        try:
            from okta.client import Client as OktaClient
        except ImportError:
            raise ImportError(
                "Could not import atlassian package. "
                "Please install it with `pip install okta`."
            )

        config = {"orgUrl": f"https://{tenant}", "token": token}
        self.client = OktaClient(config)
        self.attribute_name = attribute_name

    async def get_data_owner(self, app_name: str, **kwargs) -> User:
        qp = {"search": f'profile.{self.attribute_name} eq "{app_name}"'}
        users, _, err = await self.client.list_users(query_params=qp)
        if err is not None:
            raise ValueError(err.error_summary)

        if len(users) == 0:
            raise ValueError(f"no data owners found for app {app_name}")

        okta_data_owner = users[0]
        if okta_data_owner is None:
            return None

        if okta_data_owner.profile.email is None:
            raise ValueError("no email on okta data owner")

        user_store = factory_user_store()
        return user_store.get_by_email(email=okta_data_owner.profile.email)
