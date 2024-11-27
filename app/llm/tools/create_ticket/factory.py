from app.consts import EMAIL_CONFIG_KEY, TICKET_SYSTEM_CONFIG_KEY
from app.llm.tools.create_ticket.servicenow import ServiceNowTicketImpl
from app.models import Workspace
from app.vault_utils import resolve_ws_config_secrets

from .email import EmailTicketImpl
from .iface import TicketInterface
from .jira import JiraTicketImpl
from .mock import MockImpl
from .slack import SlackImpl


def TicketSystemFactory(ws: Workspace) -> TicketInterface:
    if TICKET_SYSTEM_CONFIG_KEY not in ws.config:
        return None

    type = ws.config[TICKET_SYSTEM_CONFIG_KEY]["type"]
    config = ws.config[TICKET_SYSTEM_CONFIG_KEY]["config"]
    resolved_config = resolve_ws_config_secrets(workspace_id=ws.id, config=config)

    match type:
        case "email":
            return EmailTicketImpl(**ws.config[EMAIL_CONFIG_KEY])
        case "jira":
            return JiraTicketImpl(**resolved_config)
        case "slack":
            return SlackImpl(**resolved_config)
        case "servicenow":
            return ServiceNowTicketImpl(**resolved_config)
        case "_mock_":
            return MockImpl(**resolved_config)

    return None
