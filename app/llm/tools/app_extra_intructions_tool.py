from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic.v1 import BaseModel, Field

from app.llm.prompts import APP_ID_KEY, APP_NAME_KEY, EXTRA_INSTRUCTIONS_KEY
from app.services import (
    factory_app_store,
)
from app.sql import SQLAlchemyTransactionContext


class FindAppInput(BaseModel):
    workspace_id: str = Field(description="workspace id of the current request")
    app_name: Optional[str] = Field(description="should be a the app name")


async def _find_app(workspace_id: str, app_name: Optional[str] = "") -> str:
    app_store = factory_app_store()
    empty_res = {
        APP_ID_KEY: None,
        APP_NAME_KEY: None,
        EXTRA_INSTRUCTIONS_KEY: "app does not exist",
    }
    if app_name is None or app_name == "":
        return empty_res

    with SQLAlchemyTransactionContext().manage() as tx_context:
        app = app_store.get_by_name(
            app_name=app_name, workspace_id=workspace_id, tx_context=tx_context
        )

        if app is None:
            return empty_res

        ei = "None" if app.extra_instructions is None else app.extra_instructions

        return {
            APP_NAME_KEY: app.unique_name,
            APP_ID_KEY: app.id,
            EXTRA_INSTRUCTIONS_KEY: ei,
        }


find_app_extra_inst_tool = StructuredTool.from_function(
    func=_find_app,
    coroutine=_find_app,
    name="find_app",
    description="finds the app name in the messages",
    args_schema=FindAppInput,
    return_direct=True,
    handle_tool_error=True,
)
