from abc import ABC, abstractmethod
from typing import List


class VaultAPI(ABC):
    @abstractmethod
    def get_secret(self, org_id: str, path: str) -> str:
        pass

    @abstractmethod
    def set_secret(self, org_id: str, path: str, value: str) -> bool:
        pass

    @abstractmethod
    def delete_secret(self, org_id: str, path: str) -> bool:
        pass

    @abstractmethod
    def list_secrets(self, org_id: str) -> List[str]:
        pass
