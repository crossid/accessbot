from typing import Any

from app.llm.tools.user_data.iface import UserDataInterface
from app.utils.strings import add_prefix


class WebhookImpl(UserDataInterface):
    url: str = ""
    user_data_url: str = ""
    user_access_url: str = ""

    def __init__(self, **kwargs) -> None:
        expected_args = ["url"]
        missing_args = [arg for arg in expected_args if arg not in kwargs]
        if missing_args:
            raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")

        self.url = kwargs.get("url")
        type_mapping = kwargs.get("type_mappings", {})
        user_type_mapping = type_mapping.get("user_data_url", "/users")
        self.user_data_url = add_prefix(user_type_mapping, "/")
        user_access_type_mapping = type_mapping.get("user_access_url", "/user_access")
        self.user_access_url = add_prefix(user_access_type_mapping, "/")

    async def get_user_data(self, user_email, **kwargs) -> dict[str, Any]:
        try:
            import requests
        except ImportError:
            raise ImportError(
                "Could not import requests package. "
                "Please install it with `pip install requests`"
            )

        body = {**kwargs, "email": user_email}
        url = f"{self.url}{self.user_data_url}"
        response = requests.post(url=url, json=body)
        if response.status_code >= 200 and response.status_code <= 399:
            return response.json()
        else:
            raise ValueError(response.text)

    async def get_user_access(
        self, user_email: str, app_names: list[str] = [], **kwargs
    ) -> dict[str, Any]:
        try:
            import requests
        except ImportError:
            raise ImportError(
                "Could not import requests package. "
                "Please install it with `pip install requests`"
            )

        body = {**kwargs, "email": user_email, "app_names": app_names}
        url = f"{self.url}{self.user_access_url}"
        response = requests.post(url=url, json=body)
        if response.status_code >= 200 and response.status_code <= 399:
            return response.json()
        else:
            raise ValueError(response.text)
