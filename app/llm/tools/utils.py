from typing import Optional

from langchain.tools import Tool

from app.models import Conversation, ConversationTypes, Workspace

from .consts import TICKET_SYSTEM_CONFIG_KEY
from .create_ticket_for_role_request_tool import request_roles


def get_tools_for_workspace_and_conversation(
    ws: Optional[Workspace], conv: Conversation
) -> list[Tool]:
    _tools: list[Tool] = []
    if ws is None:
        return _tools

    if (
        TICKET_SYSTEM_CONFIG_KEY in ws.config
        and conv.type == ConversationTypes.recommendation
    ):
        _tools.append(request_roles)

    return _tools
