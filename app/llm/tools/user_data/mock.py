from typing import Any

from app.llm.tools.user_data.iface import UserAccess, UserDataInterface


class MockImpl(UserDataInterface):
    def __init__(self) -> None:
        pass

    async def get_user_data(self, user_email, **kwargs) -> dict[str, Any]:
        return {"email": "jon.doe@vandelay.com"}

    async def get_user_access(
        self, user_email: str, app_names: list[str] = [], **kwargs
    ) -> dict[str, list[UserAccess]]:
        return {"mock": [UserAccess(id="foo")]}
