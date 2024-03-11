from typing import Any

from app.vault_utils import resolve_ws_config_secrets

from .email import EmailTicketImpl
from .iface import TicketInterface
from .jira import JiraTicketImpl
from .mock import MockImpl
from .slack import SlackImpl


def TicketSystemFactory(
    workspace_id: str, type: str, config: dict[str, Any]
) -> TicketInterface:
    resolved_config = resolve_ws_config_secrets(
        workspace_id=workspace_id, config=config
    )

    match type:
        case "email":
            return EmailTicketImpl(**resolved_config)
        case "jira":
            return JiraTicketImpl(**resolved_config)
        case "slack":
            return SlackImpl(**resolved_config)
        case "_mock_":
            return MockImpl(**resolved_config)

    return None
