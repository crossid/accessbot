from app.id import generate
from app.models import User
from app.utils.emails.factory import EmailFactory
from app.utils.emails.iface import EmailSenderInterface

from .iface import TicketInterface


class EmailTicketImpl(TicketInterface):
    email_sender: EmailSenderInterface
    sender_email = "noreply@crossid.io"
    subject = "Role Request waiting for you"

    def __init__(self, **kwargs) -> None:
        _type = kwargs.get("type")
        _config = kwargs.get("config")
        self.email_sender = EmailFactory(_type, _config)

    def create_ticket(
        self,
        content: str,
        owner: User,
        requester: User,
        app_name: str,
        conv_summary: str,
        conversation_id: str,
        workspace_id: str,
        **kwargs,
    ) -> str:
        self.email_sender.send(
            from_addr=self.sender_email,
            to=owner.email,
            msg=content,
            subject=self.subject,
        )

        return generate()
