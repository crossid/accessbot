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
        role_name: str,
        access: str,
        conv_summary: str,
        conversation_id: str,
        workspace_id: str,
    ):
        owner.full_name = content
