from .iface import DataOwnerInterface


class MockImpl(DataOwnerInterface):
    attribute_name: str

    def __init__(self) -> None:
        pass

    async def get_data_owner(self, app_name: str, **kwargs) -> str:
        return None
