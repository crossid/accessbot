from abc import ABC, abstractmethod
from typing import Any


class UserDataInterface(ABC):
    @abstractmethod
    async def get_user_data(self, user_email, **kwargs) -> dict[str, Any]:
        pass
