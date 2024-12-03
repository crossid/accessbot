from abc import ABC, abstractmethod
from typing import Any, List

from pydantic import BaseModel, ConfigDict


class UserAccess(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str


class UserDataInterface(ABC):
    @abstractmethod
    async def list_users_data(self, **kwargs) -> List[dict[str, Any]]:
        """
        returns a list of dictionaries with the user's data. Doesn't necessarily include the user's access.
        """
        pass

    @abstractmethod
    async def get_user_data(self, user_email: str, **kwargs) -> dict[str, Any]:
        """
        returns a dictionary with the user's data. Doesn't necessarily include the user's access.
        """
        pass

    @abstractmethod
    async def get_user_access(
        self, user_email: str, app_names: list[str] = [], **kwargs
    ) -> dict[str, list[UserAccess]]:
        """
        returns a dictionary of app_name to list of user access
        """

        pass
