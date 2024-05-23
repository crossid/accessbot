from abc import ABC, abstractmethod

from app.models import User


class DataOwnerInterface(ABC):
    @abstractmethod
    async def get_data_owner(self, app_name: str, **kwargs) -> User:
        pass
