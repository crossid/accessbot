from abc import ABC, abstractmethod

from app.models import User


class TicketInterface(ABC):
    @abstractmethod
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
        pass
