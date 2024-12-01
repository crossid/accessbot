import requests

from app.models import User

from .iface import TicketInterface


class ServiceNowTicketImpl(TicketInterface):
    instance: str
    username: str
    password: str
    table: str
    # static ticket parameters to add to each ticket
    ticket_params: dict[str, str] = {}

    def __init__(
        self,
        instance: str,
        username: str,
        password: str,
        ticket_params: dict[str, str],
        table: str = "incident",
    ) -> None:
        self.instance = instance
        self.username = username
        self.password = password
        self.table = table
        self.ticket_params = ticket_params
        self.base_url = f"https://{instance}.service-now.com/api/now/v1/table/{table}"

    def create_ticket(
        self,
        content: str,
        owner: User,
        requester: User,
        conv_summary: str,
        conv_lang: str,
        conversation_id: str,
        workspace_id: str,
        app_name: str,
        **kwargs,
    ) -> str:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # Find the user ID in ServiceNow by the user's email
        user_url = f"https://{self.instance}.service-now.com/api/now/v1/table/sys_user"
        user_params = {"email": requester.email}
        user_response = requests.get(
            user_url,
            auth=(self.username, self.password),
            headers=headers,
            params=user_params,
        )

        if user_response.status_code != 200:
            raise Exception(f"Failed to find user: {user_response.text}")

        user_result = user_response.json()
        if not user_result["result"]:
            raise Exception(f"No user found with email: {requester.email}")

        requester_id = user_result["result"][0]["sys_id"]

        payload = {
            "short_description": conv_summary[:160],
            "description": content,
            "caller_id": requester_id,
            "comments": "\n".join(f"{k}: {v}" for k, v in kwargs.items()),
            # I expect this to be assigned by service now business rules
            # "assigned_to": owner.email,
        }

        # Add the static ticket parameters to the payload, without overwriting any existing keys
        payload = {**self.ticket_params, **payload}

        response = requests.post(
            self.base_url,
            auth=(self.username, self.password),
            headers=headers,
            json=payload,
        )

        if response.status_code != 201:
            raise Exception(f"Failed to create ticket: {response.text}")

        result = response.json()
        return result["result"]["number"]
