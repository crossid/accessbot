from app.models import User

from .iface import TicketInterface


class MockImpl(TicketInterface):
    def __init__(self) -> None:
        pass

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
    ):
        print(f"__mock impl__ \ncontent: {content}\n kwargs: {kwargs}")
        owner.full_name = content
        return content
