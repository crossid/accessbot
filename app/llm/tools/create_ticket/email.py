import smtplib
from email.mime.text import MIMEText

from app.id import generate
from app.models import User

from .iface import TicketInterface


class EmailTicketImpl(TicketInterface):
    host: str
    sender_email = "noreply@crossid.io"
    subject = "Role Request waiting for you"

    def __init__(self, host) -> None:
        self.host = host

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
        msg = MIMEText(content)
        msg["Subject"] = self.subject
        host, port = self.host.split(":")
        with smtplib.SMTP(host, port) as server:
            server.sendmail(
                from_addr=self.sender_email, to_addrs=owner.email, msg=msg.as_string()
            )

        return generate()
