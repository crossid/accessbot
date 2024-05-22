from .iface import ProvisionInterface


class WebhookImpl(ProvisionInterface):
    url: str = ""

    def __init__(self, **kwargs) -> None:
        expected_args = ["url"]
        missing_args = [arg for arg in expected_args if arg not in kwargs]
        if missing_args:
            raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")

        self.url = kwargs.get("url")

    async def approve_request(self, requester_email: str, **kwargs) -> bool:
        try:
            import requests
        except ImportError:
            raise ImportError(
                "Could not import requests package. "
                "Please install it with `pip install requests`"
            )

        body = {**kwargs, "requester_email": requester_email}
        try:
            response = requests.post(url=self.url, json=body)
            return response.status_code >= 200 and response.status_code <= 399
        except Exception:
            # logger
            return False
