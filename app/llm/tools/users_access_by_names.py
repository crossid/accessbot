from langchain_core.tools import StructuredTool, ToolException
from pydantic.v1 import BaseModel, Field

from app.llm.tools.user_data.factory import GetUserDataFactory
from app.services import factory_dir_store, factory_ws_store
from app.sql import SQLAlchemyTransactionContext


class UsersDetailsToolData(BaseModel):
    app_name: str = Field(description="the app name")
    directory_id: str = Field(description="the directory id")
    users_names: list[str] = Field(description="the user's email address")


def _users_details_from_names_wrapper(workspace_id: str):
    async def _users_details_from_names(
        app_name: str, directory_id: str, users_names: list[str], **kwargs
    ) -> str:
        dir_store = factory_dir_store()
        ws_store = factory_ws_store()
        with SQLAlchemyTransactionContext().manage() as tx_context:
            dir = dir_store.get_by_id(
                directory_id="-Ci2o1lpxL",
                workspace_id=workspace_id,
                tx_context=tx_context,
            )
            ws = ws_store.get_by_id(workspace_id=workspace_id, tx_context=tx_context)
            if dir is None or ws is None:
                raise ToolException(
                    f"could not find directory: {directory_id} or workspace {workspace_id}"
                )

        udi = GetUserDataFactory(workspace=ws, directory=dir)
        users_data = await udi.get_user_data_for_names(
            names=users_names, app_name=app_name
        )

        return users_data

    return _users_details_from_names


def create_users_details_from_names_tool(ws_id: str) -> StructuredTool:
    fetch_relevant_data_tool = StructuredTool.from_function(
        coroutine=_users_details_from_names_wrapper(workspace_id=ws_id),
        name="get_users_data_by_names",
        description="fetches users data by their names",
        args_schema=UsersDetailsToolData,
        handle_tool_error=True,
    )

    return fetch_relevant_data_tool
