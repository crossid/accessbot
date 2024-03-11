from .iface import ProvisionInterface


class MockImpl(ProvisionInterface):
    def __init__(self) -> None:
        pass

    async def approve_request(self, requester_email: str, **kwargs) -> bool:
        print(f"Requested by: {requester_email}")
        print(f"kwargs: {kwargs}")
        return True
