from typing import Any, Optional

from langchain.tools import Tool
from pydantic import BaseModel, Field, create_model

from app.i18n import i18n
from app.models import Conversation, Workspace
from app.models_stores import ConversationStore
from app.services import (
    factory_app_store,
)
from app.sql import SQLAlchemyTransactionContext


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


def _create_expanded_model(
    base_model: dict[str, dict[str, Any]], model_name: str, extra_fields: dict
):
    fields = {
        k: (info["type"], Field(description=info["description"]))
        for k, info in base_model.items()
    }
    efields = {
        k: (str, Field(description=info["description"]))
        for k, info in extra_fields.items()
    }

    all_fields = {**fields, **efields}

    dynamic_model = create_model(
        f"Dynamic{model_name}", __base__=BaseModel, **all_fields
    )

    return dynamic_model


def create_expanded_model(
    app_id: str,
    ws_id: str,
    base_model: dict[str, dict[str, Any]],
    model_name: str,
    default_extra_fields={},
):
    extra_fields = default_extra_fields
    app_store = factory_app_store()
    with SQLAlchemyTransactionContext().manage() as tx_context:
        app = app_store.get_by_id(
            app_id=app_id, workspace_id=ws_id, tx_context=tx_context
        )
        if app is not None and app.provision_schema is not None:
            extra_fields = app.provision_schema

    return _create_expanded_model(
        base_model=base_model, model_name=model_name, extra_fields=extra_fields
    )


def update_conv(
    conv_store: ConversationStore,
    status: str,
    conv_summary: str,
    workspace_id: str,
    conversation_id: str,
    tx_context,
):
    updates: dict[str, Any] = {
        "status": status,
        "summary": conv_summary,
    }
    conv_store.update(
        workspace_id=workspace_id,
        conversation_id=conversation_id,
        updates=updates,
        tx_context=tx_context,
    )


class MsgContent:
    full: str
    approval_q: str

    def __init__(self, full: str, approval_q: str):
        self.full = full
        self.approval_q = approval_q


def get_do_msg_content(
    lang: str, requester: str, conv_summary: str, app_name: str, **kwargs
) -> MsgContent:
    i = i18n(lang=lang)
    approval_q = i.t("approval_q").capitalize()
    kwargs_str = "\n".join(f"- {i.t(key)}: {value}" for key, value in kwargs.items())
    full = f"""
{i.t("hello")}, {i.t("request_waiting")}: {requester}.\n\n
**{i.t("basic_info")}**:
- {i.t("app_name").capitalize()}: {app_name}
- {i.t("summary").capitalize()}: {conv_summary}\n
\n
**{i.t("my_recommendation").capitalize()}**:\n
{kwargs_str}
\n
{approval_q}
"""

    msg = MsgContent(full=full, approval_q=approval_q)
    return msg
