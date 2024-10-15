from typing import Any, List, Optional

from app.email_comms.google_cloud.gmail_utils import create_message, gmail_authenticate
from app.utils.emails.iface import EmailSenderInterface


class GmailImpl(EmailSenderInterface):
    service: Any
    email_address: str

    def __init__(self, client_id: str, client_secret: str, email_address: str) -> None:
        service = gmail_authenticate(client_id, client_secret, email_address)
        self.service = service
        self.email_address = email_address

    def send(
        self,
        from_addr: str,
        to: str | List[str],
        content: str,
        subject: str,
        content_type: Optional[str] = None,
    ) -> bool:
        msg = create_message(
            sender=self.email_address, to=to, subject=subject, message_text=content
        )
        self.service.users().messages().send(
            userId=self.email_address, body=msg
        ).execute()
        return True
