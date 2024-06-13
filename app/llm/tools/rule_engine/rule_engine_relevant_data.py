from langchain_core.tools import StructuredTool
from pydantic.v1 import BaseModel, Field

from app.llm.tools.utils import create_expanded_model


class RelevantDataInput(BaseModel):
    workspace_id: str = Field(description="the workspace id")
    app_name: str = Field(description="the app id")
    directory_name: str = Field(description="the directory name")
    user_email: str = Field(description="the user's email address")


def _get_relevant_data(**kwargs) -> str:
    # data = {
    #     "app": {"sensitivity": 2},
    #     "working_hours": "9am to 5pm",
    #     "access": {"sensitivity": 5, "description": "can write cheques"},
    #     "request": {"created_at": datetime.now()},
    #     "user": {"known_access": [{"description": "can sign cheques"}]},
    #     "approve_rules": approve_rules,
    #     "deny_rules": deny_rules,
    # }
    return {}


def create_relevant_data_tool(app_id: str, ws_id: str) -> StructuredTool:
    dynamic_model = create_expanded_model(
        app_id=app_id,
        ws_id=ws_id,
        base_model=RelevantDataInput,
        model_name="RelevantDataInput",
    )

    fetch_relevant_data_tool = StructuredTool.from_function(
        func=_get_relevant_data,
        coroutine=_get_relevant_data,
        name="get_relevant_data",
        description="fetches relevant data for rules assessment",
        args_schema=dynamic_model,
        handle_tool_error=True,
    )

    return fetch_relevant_data_tool
