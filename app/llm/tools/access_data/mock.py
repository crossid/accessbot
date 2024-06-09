from typing import Any

from app.llm.tools.access_data.iface import AccessDataInterface


class MockImpl(AccessDataInterface):
    def __init__(self) -> None:
        pass

    async def get_access_data(self, app_name: str, **kwargs) -> dict[str, Any]:
        return {"sensitivity": 5, "description": "grants read and write access"}
