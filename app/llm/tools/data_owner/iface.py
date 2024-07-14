from abc import ABC, abstractmethod


class DataOwnerInterface(ABC):
    @abstractmethod
    async def get_data_owner(self, app_name: str, **kwargs) -> str:
        pass
