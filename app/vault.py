from abc import ABC, abstractmethod


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
