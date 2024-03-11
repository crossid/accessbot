from abc import ABC, abstractmethod


class ProvisionInterface(ABC):
    # rolename: role's id in the app
    # requester_email: The email of the user who requested the role
    @abstractmethod
    async def approve_request(self, rolename: str, requester_email: str) -> bool:
        pass
