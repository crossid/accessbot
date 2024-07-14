import smtplib
from email.mime.text import MIMEText
from typing import List, Optional

from app.utils.emails.iface import EmailSenderInterface


class SMTPImpl(EmailSenderInterface):
    host: str
    port: int

    def __init__(self, host: str) -> None:
        host_port = host.split(":")
        self.host = host_port[0]
        self.port = int(host_port[1])

    def send(
        self,
        from_addr: str,
        to: str | List[str],
        content: str,
        subject: str,
        content_type: Optional[str] = None,
    ) -> bool:
        msg = MIMEText(content, content_type)
        msg["Subject"] = subject

        with smtplib.SMTP(self.host, self.port) as server:
            server.sendmail(from_addr=from_addr, to_addrs=to, msg=msg.as_string())

        return True
