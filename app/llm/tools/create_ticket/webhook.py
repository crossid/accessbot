from app.models import User

from .iface import TicketInterface


class WebhookImpl(TicketInterface):
    url: str = ""
    ticket_id_field: str = ""

    def __init__(self, **kwargs) -> None:
        expected_args = ["url"]
        missing_args = [arg for arg in expected_args if arg not in kwargs]
        if missing_args:
            raise ValueError(f"Missing required arguments: {', '.join(missing_args)}")

        self.url = kwargs.get("url")
        self.ticket_id_field = kwargs.get("ticket_id", "ticket_id")

    def create_ticket(
        self,
        content: str,
        owner: User,
        requester: User,
        conv_summary: str,
        conversation_id: str,
        workspace_id: str,
        app_name: str,
        **kwargs,
    ) -> str:
        try:
            import requests
        except ImportError:
            raise ImportError(
                "Could not import requests package. "
                "Please install it with `pip install requests`"
            )

        body = {
            **kwargs,
            "owner": owner,
            "requester": requester,
            "conversation_id": conversation_id,
            "app_name": app_name,
        }
        response = requests.post(url=self.url, json=body)
        if response.status_code >= 200 and response.status_code <= 399:
            jresp = response.json()
            return jresp.get(self.ticket_id_field, None)
        else:
            raise ValueError(response.text)
