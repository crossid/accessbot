import asyncio
import functools
import json

from langchain_core.messages import FunctionMessage, HumanMessage
from langchain_core.pydantic_v1 import BaseModel, Field

from app.llm.tools.deny_access_tool import create_deny_provision_tool
from app.models import ConversationTypes

from .agents import create_agent
from .prompts import (
    APP_ID_KEY,
    APP_NAME_KEY,
    DATA_OWNER_TEMPLATE,
    ENTRY_POINT,
    EXTRA_INSTRUCTIONS_KEY,
    INFO_AGENT_TEMPLATE,
    MEMORY_KEY,
    RECOMMENDATION_TEMPLATE,
    WS_ID_KEY,
    get_prompt,
)
from .tools.app_extra_intructions_tool import find_app_extra_inst_tool
from .tools.create_ticket_for_role_request_tool import create_request_roles_tool
from .tools.provision_role_tool import create_provision_role_tool

INFORMATION_AGENT_NAME = "Information"
RECOMMENDER_AGENT_NAME = "Recommender"
DATA_OWNER_AGENT_NODE = "Data Owner"
CONV_TYPE_DATA_OWNER = ConversationTypes.data_owner.value
CONV_TYPE_INFO = ConversationTypes.recommendation.value


def agent_node(state, agent_creator, name):
    agent = agent_creator(state)
    result = asyncio.new_event_loop().run_until_complete(agent.ainvoke(state))
    # We convert the agent output into a format that is suitable to append to the global state
    if isinstance(result, FunctionMessage):
        pass
    else:
        result = HumanMessage(content=result["output"], name=name)

    return {
        MEMORY_KEY: [result],
        "sender": name if name != RECOMMENDER_AGENT_NAME else state["sender"],
    }


def create_data_owner_node(data_context):
    def agent_creator(state):
        app_id = state.get("app_id", None)
        prt = create_provision_role_tool(
            app_id=app_id, ws_id=data_context.get(WS_ID_KEY)
        )
        dpt = create_deny_provision_tool(
            app_id=app_id, ws_id=data_context.get(WS_ID_KEY)
        )
        do_agent = create_agent(
            prompt=get_prompt(prompt_id=DATA_OWNER_TEMPLATE, data_context=data_context),
            tools=[prt, dpt],
            name=DATA_OWNER_AGENT_NODE,
        )

        return do_agent

    data_owner_node = functools.partial(
        agent_node, agent_creator=agent_creator, name=DATA_OWNER_AGENT_NODE
    )

    return data_owner_node


def create_info_gatherer_node(data_context):
    def agent_creator(state):
        app_id = state.get("app_id", None)
        rrt = create_request_roles_tool(
            app_id=app_id, ws_id=data_context.get(WS_ID_KEY)
        )
        _dctx = data_context.copy()
        _dctx[EXTRA_INSTRUCTIONS_KEY] = state[EXTRA_INSTRUCTIONS_KEY]
        info_agent = create_agent(
            prompt=get_prompt(prompt_id=INFO_AGENT_TEMPLATE, data_context=_dctx),
            tools=[rrt],
            name=INFORMATION_AGENT_NAME,
        )

        return info_agent

    info_gatherer_node = functools.partial(
        agent_node, agent_creator=agent_creator, name=INFORMATION_AGENT_NAME
    )

    return info_gatherer_node


def create_recommend_agent(data_context, ret_tool):
    def agent_creator(state):
        _dctx = data_context.copy()
        _dctx[APP_NAME_KEY] = state[APP_NAME_KEY]
        _dctx[EXTRA_INSTRUCTIONS_KEY] = state[EXTRA_INSTRUCTIONS_KEY]
        agent = create_agent(
            prompt=get_prompt(
                prompt_id=RECOMMENDATION_TEMPLATE, data_context=data_context
            ),
            tools=[ret_tool],
            name=RECOMMENDER_AGENT_NAME,
        )
        return agent

    return agent_creator


def create_recommendation_node(data_context, ret_tool):
    rec_agent = create_recommend_agent(data_context=data_context, ret_tool=ret_tool)
    recommendation_node = functools.partial(
        agent_node, agent_creator=rec_agent, name=RECOMMENDER_AGENT_NAME
    )

    return recommendation_node


class IGNOutput(BaseModel):
    extra_instructions: str = Field(description="extra instructions for the app")
    app_id: str = Field(description="the app id")
    app_name: str = Field(description="the app name")


def entry_point_node(data_context):
    def _epn(state):
        if state.get("conv_type") == CONV_TYPE_DATA_OWNER:
            return {
                "sender": "entry_point",
            }

        msgs = []
        agent = create_agent(
            prompt=get_prompt(prompt_id=ENTRY_POINT, data_context=data_context),
            tools=[find_app_extra_inst_tool],
            name="entry_point",
            streaming=False,
        )

        result = asyncio.new_event_loop().run_until_complete(agent.ainvoke(state))
        output = result["output"]
        json_string = output.strip("```json\n")
        json_output = json.loads(json_string)
        # extra_ins = json_output[EXTRA_INSTRUCTIONS_KEY]
        # if json_output.get(APP_ID_KEY) != state.get(APP_ID_KEY) and extra_ins != "None":
        #     msgs.append(SystemMessage(content=extra_ins))

        return {
            MEMORY_KEY: msgs,
            "sender": "entry_point",
            APP_ID_KEY: json_output[APP_ID_KEY],
            APP_NAME_KEY: json_output[APP_NAME_KEY],
            EXTRA_INSTRUCTIONS_KEY: json_output[EXTRA_INSTRUCTIONS_KEY],
        }

    return _epn
