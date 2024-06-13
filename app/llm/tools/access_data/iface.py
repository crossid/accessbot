from abc import ABC, abstractmethod
from typing import Any


class AccessDataInterface(ABC):
    @abstractmethod
    async def get_access_data(self, app_name: str, **kwargs) -> dict[str, Any]:
        pass
