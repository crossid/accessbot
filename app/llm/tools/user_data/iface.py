from abc import ABC, abstractmethod
from typing import Any


class UserDataInterface(ABC):
    @abstractmethod
    async def get_user_data(self, user_email: str, **kwargs) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_user_access(
        self, user_email: str, app_names: list[str] = [], **kwargs
    ) -> dict[str, Any]:
        pass
