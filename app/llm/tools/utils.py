from typing import Optional

from langchain.tools import Tool

from app.models import Conversation, Workspace


def get_tools_for_workspace_and_conversation(
    ws: Optional[Workspace], conv: Conversation
) -> list[Tool]:
    _tools: list[Tool] = []
    if ws is None:
        return _tools

    # if TICKET_SYSTEM_CONFIG_KEY in ws.config:
    #     _tools.append(request_roles_tool)

    # if PROVISION_CONFIG_KEY in ws.config:
    #     _tools.append(provision_roles_tool)

    return _tools
