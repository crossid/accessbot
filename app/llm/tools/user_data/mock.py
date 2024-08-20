from typing import Any

from app.llm.tools.user_data.iface import UserDataInterface


class MockImpl(UserDataInterface):
    known_people = {
        "john.doe@vandaly.com": {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john.doe@vandaly.com",
            "access": {"projects": [16]},
        },
        "sarah.smith@vandaly.com": {
            "firstName": "Sarah",
            "lastName": "Smith",
            "email": "sarah.smith@vandaly.com",
            "access": {"projects": [16]},
        },
        "michael.johnson@vandaly.com": {
            "firstName": "Michael",
            "lastName": "Johnson",
            "email": "michael.johnson@vandaly.com",
            "access": {"projects": [1]},
        },
        "emily.chen@vandaly.com": {
            "firstName": "Emily",
            "lastName": "Chen",
            "email": "emily.chen@vandaly.com",
            "access": {"projects": [1]},
        },
        "robert.williams@vandaly.com": {
            "firstName": "Robert",
            "lastName": "Williams",
            "email": "robert.williams@vandaly.com",
            "access": {"projects": [2]},
        },
    }

    def __init__(self) -> None:
        pass

    async def get_user_data(self, user_email, **kwargs) -> dict[str, Any]:
        return self.known_people.get("john.doe@vandaly.com")

    async def get_user_data_for_names(
        self, names: list[str], **kwargs
    ) -> dict[str, Any]:
        return self.known_people
