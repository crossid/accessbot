from .iface import ProvisionInterface


class MockImpl(ProvisionInterface):
    def __init__(self) -> None:
        pass

    async def approve_request(self, rolename: str, requester_email: str) -> bool:
        print(f"Role: {rolename} requested by: {requester_email}")
        return True
