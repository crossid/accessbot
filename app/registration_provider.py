from abc import ABC, abstractmethod
from typing import Optional

from app.settings import settings


class RegistrationEmailParams:
    from_addr: str
    content: str
    content_type: Optional[str] = None
    subject: str

    def __init__(
        self,
        from_addr: str,
        content: str,
        subject: str,
        content_type: Optional[str] = None,
    ):
        self.from_addr = from_addr
        self.content = content
        self.content_type = content_type
        self.subject = subject


class RegistrationProviderInterface(ABC):
    @abstractmethod
    def get_registration_email(self, workspace_id: str) -> RegistrationEmailParams:
        pass


class DefaultRegistrationProvider:
    from_addr = "noreply@crossid.io"
    subject = "Registration Required"

    def create_content(self) -> str:
        return f"Hello, you've been invited to Accessbot service.\nPlease register to the service with the link below:\n{settings.REGISTRATION_URL_TEMPLATE}"

    def get_registration_email(self, workspace_id: str) -> RegistrationEmailParams:
        email_params = RegistrationEmailParams(
            from_addr=self.from_addr,
            content=self.create_content(),
            subject=self.subject,
        )

        return email_params
