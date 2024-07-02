from typing import Any

from app.llm.tools.access_data.iface import AccessDataInterface
from app.utils.strings import add_prefix


class WebhookImpl(AccessDataInterface):
    url: str = ""
    access_data_url: str = ""

    def __init__(self, **kwargs) -> None:
        expected_args = ["url"]
        missing_args = [arg for arg in expected_args if arg not in kwargs]
        if missing_args:
            raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")

        self.url = kwargs.get("url")
        type_mapping = kwargs.get("type_mappings", {}).get("access_data_url", "/access")
        self.access_data_url = add_prefix(type_mapping, "/")

    async def get_access_data(self, app_name: str, **kwargs) -> dict[str, Any]:
        try:
            import requests
        except ImportError:
            raise ImportError(
                "Could not import requests package. "
                "Please install it with `pip install requests`"
            )

        body = {**kwargs, "app_name": app_name}
        url = f"{self.url}{self.access_data_url}"
        response = requests.post(url=url, json=body)
        if response.status_code >= 200 and response.status_code <= 399:
            return response.json()
        else:
            raise ValueError(response.text)
