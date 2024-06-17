from typing import Any

from app.llm.tools.user_data.iface import UserDataInterface


class MockImpl(UserDataInterface):
    def __init__(self) -> None:
        pass

    async def get_user_data(self, user_email, **kwargs) -> dict[str, Any]:
        return {"email": "jon.doe@vandelay.com"}
