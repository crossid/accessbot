from langchain_core.tools import StructuredTool
from pydantic.v1 import BaseModel, Field

from app.llm.tools.access_data.factory import GetAccessDataFactory
from app.llm.tools.user_data.factory import GetUserDataFactory
from app.llm.tools.utils import create_expanded_model
from app.services import factory_dir_store, factory_ws_store
from app.sql import SQLAlchemyTransactionContext


class RelevantDataInput(BaseModel):
    workspace_id: str = Field(description="the workspace id")
    app_name: str = Field(description="the app name")
    directory_id: str = Field(description="the directory id")
    user_email: str = Field(description="the user's email address")


async def _get_relevant_data(
    workspace_id: str, app_name: str, directory_id: str, user_email: str, **kwargs
) -> str:
    dir_store = factory_dir_store()
    ws_store = factory_ws_store()
    with SQLAlchemyTransactionContext().manage() as tx_context:
        dir = dir_store.get_by_id(
            directory_id=directory_id, workspace_id=workspace_id, tx_context=tx_context
        )
        ws = ws_store.get_by_id(workspace_id=workspace_id, tx_context=tx_context)
        if dir is None or ws is None:
            raise ValueError(
                f"could not find directory: {directory_id} or workspace {workspace_id}"
            )

    udi = GetUserDataFactory(workspace=ws, directory=dir)
    user_data = (
        await udi.get_user_data(user_email=user_email, **kwargs)
        if udi is not None
        else {"email": user_email}
    )
    adi = GetAccessDataFactory(workspace=ws, directory=dir)
    access_data = (
        await adi.get_access_data(app_name=app_name, **kwargs)
        if adi is not None
        else {}
    )
    return {"user": user_data, "access": access_data}


def create_relevant_data_tool(app_id: str, ws_id: str) -> StructuredTool:
    dynamic_model = create_expanded_model(
        app_id=app_id,
        ws_id=ws_id,
        base_model=RelevantDataInput,
        model_name="RelevantDataInput",
    )

    fetch_relevant_data_tool = StructuredTool.from_function(
        coroutine=_get_relevant_data,
        name="get_relevant_data",
        description="fetches relevant data for rules assessment",
        args_schema=dynamic_model,
        handle_tool_error=True,
    )

    return fetch_relevant_data_tool
