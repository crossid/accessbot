from app.models import User

from .iface import DataOwnerInterface


class MockImpl(DataOwnerInterface):
    dataowner: User

    def __init__(self, **kwargs) -> None:
        do = User()
        do.disabled = False
        do.email = kwargs.get("email", "erez@crossid.io")
        do.full_name = kwargs.get("full_name", "John Doe")
        do.id = kwargs.get("id", "1")
        self.dataowner = do

    async def get_data_owner(self, rolename: str) -> User:
        return self.dataowner
