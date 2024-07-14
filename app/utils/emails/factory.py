from typing import Any

from app.consts import EMAIL_CONFIG_KEY
from app.models import Workspace
from app.utils.emails.iface import EmailSenderInterface
from app.utils.emails.smtp import SMTPImpl
from app.vault_utils import resolve_ws_config_secrets


def EmailFactoryForWS(ws: Workspace) -> EmailSenderInterface:
    email_type = ws.config[EMAIL_CONFIG_KEY].get("type")
    email_config = resolve_ws_config_secrets(
        ws.id, ws.config[EMAIL_CONFIG_KEY].get("config")
    )
    return EmailFactory(email_type, email_config)


# config needs to be resolved before it gets here
def EmailFactory(type: str, config: dict[str, Any]) -> EmailSenderInterface:
    match type:
        case "smtp":
            return SMTPImpl(**config)

    return None
