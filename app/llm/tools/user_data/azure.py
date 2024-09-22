import logging
from typing import Any

from app.llm.tools.user_data.iface import UserDataInterface
from app.utils.azure_client import get_azure_client, get_users_by_filter

logger = logging.getLogger(__name__)


class AzureImpl(UserDataInterface):
    default_select: list[str] = ["id", "displayName", "mail", "accountEnabled"]
    default_expand: list[str] = ["memberOf"]
    configurable_select: list[str] = []
    configurable_expand: list[str] = []

    def __init__(self, **kwargs) -> None:
        self.client = get_azure_client()
        self.configurable_select = kwargs.get("select", []) - self.default_select
        self.configurable_expand = kwargs.get("expand", []) - self.default_expand

    async def get_user_data(self, user_email, **kwargs) -> dict[str, Any]:
        select = self.default_select + self.configurable_select
        expand = self.default_expand + self.configurable_expand
        filter = f"mail eq '{user_email}'"
        users = await get_users_by_filter(
            filter=filter, select=select, expand=expand, client=self.client
        )
        if len(users.value) == 0:
            return {}

        user = users.value[0]
        return {
            "id": user.id,
            "name": user.display_name,
            "email": user.mail,
            "enabled": user.account_enabled,
            "member_of": [
                {
                    "id": group.id,
                    "name": group.display_name,
                    "description": group.description,
                }
                for group in user.member_of
            ],
            **{attr: getattr(user, attr, None) for attr in self.configurable_select},
        }
