from typing import Optional

from langchain.tools import Tool
from pydantic.v1 import BaseModel, Field, create_model

from app.models import Conversation, Workspace
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


def create_expanded_model(
    app_id: str, ws_id: str, base_model: BaseModel, model_name: str
):
    app_store = factory_app_store()
    extra_fields = {"role_name": {"description": "should be a the role name"}}
    with SQLAlchemyTransactionContext().manage() as tx_context:
        app = app_store.get_by_id(
            app_id=app_id, workspace_id=ws_id, tx_context=tx_context
        )
        if app is not None and app.provision_schema is not None:
            extra_fields = app.provision_schema

    fields = {
        k: (str, Field(description=info["description"]))
        for k, info in extra_fields.items()
    }
    dynamic_model = create_model(f"Dynamic{model_name}", __base__=base_model, **fields)

    return dynamic_model
