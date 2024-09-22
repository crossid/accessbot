import asyncio
import logging
from typing import List, Optional

from app.models import User
from app.models_stores import UserStore
from app.utils.azure_client import (
    get_azure_client,
    get_organization,
    get_users_by_filter,
)

logger = logging.getLogger(__name__)


def azure_user_to_user(user) -> User:
    return User(
        id=user.id,
        email=user.mail,
        full_name=user.display_name,
        disabled=not user.account_enabled if user.account_enabled is not None else None,
    )


class AzureUserStore(UserStore):
    def __init__(self):
        self.client = get_azure_client()

    async def _get_by_email(self, email: str) -> Optional[User]:
        from kiota_abstractions.api_error import APIError

        select = ["id", "displayName", "mail", "accountEnabled"]
        filter = f"mail eq '{email}'"

        try:
            users = await get_users_by_filter(
                filter=filter, select=select, client=self.client
            )
            if len(users.value) == 0:
                return None

            return azure_user_to_user(users.value[0])
        except APIError as e:
            logger.debug(f"no user found, {e.error.message}")
            return None

    def get_by_email(self, email: str) -> Optional[User]:
        return asyncio.run(self._get_by_email(email))

    async def _list_workspaces_for_user(self, user_id: str) -> List[str]:
        from kiota_abstractions.api_error import APIError

        select = ["id"]

        try:
            result = await get_organization(select, self.client)
            return [result.value[0].id]
        except APIError as e:
            logger.debug(f"no user found, {e.error.message}")
            return []

    def list_workspaces_for_user(self, user_id: str) -> List[str]:
        return asyncio.run(self._list_workspaces_for_user(user_id))

    def add_user_to_workspace(self, user_id: str, workspace_id: str):
        return NotImplementedError("Not implemented")
