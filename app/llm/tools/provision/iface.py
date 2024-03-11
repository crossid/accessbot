from abc import ABC, abstractmethod


class ProvisionInterface(ABC):
    # rolename: role's id in the app
    # requester_email: The email of the user who requested the role
    @abstractmethod
    async def approve_request(self, requester_email: str, **kwargs) -> bool:
        pass
