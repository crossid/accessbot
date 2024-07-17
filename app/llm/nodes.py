import asyncio
import functools
import json
from types import coroutine

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.llm.guardrails.on_topic import topical_guardrail
from app.llm.tools.deny_access_tool import create_deny_provision_tool
from app.models import ConversationTypes
from app.settings import settings

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
DATA_OWNER_AGENT_NODE = "DataOwner"
CONVERSATION_TYPE_KEY = "conv_type"
CONV_TYPE_DATA_OWNER = ConversationTypes.data_owner.value
CONV_TYPE_INFO = ConversationTypes.recommendation.value
CONV_TYPE_FAILED_GUARD = "FAILED_GUARD"


def agent_node(state, agent_creator, name):
    agent = agent_creator(state)
    result = asyncio.new_event_loop().run_until_complete(agent.ainvoke(state))
    # We convert the agent output into a format that is suitable to append to the global state
    if isinstance(result, ToolMessage):
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


async def execute_chat_with_guardrail(runnable: coroutine, input):
    topical_guardrail_task = asyncio.create_task(topical_guardrail(input))
    chat_task = asyncio.create_task(runnable)
    while True:
        done, _ = await asyncio.wait(
            [topical_guardrail_task, chat_task], return_when=asyncio.FIRST_COMPLETED
        )
        if topical_guardrail_task in done:
            guardrail_response = topical_guardrail_task.result()
            if not guardrail_response.is_valid:
                chat_task.cancel()
                return {
                    "output": "I'm sorry, I can only talk about access requests"
                }, False
            elif chat_task in done:
                result = chat_task.result()
                return result, True
        else:
            await asyncio.sleep(0.2)


def entry_point_node(data_context):
    def _epn(state):
        agent = create_agent(
            prompt=get_prompt(prompt_id=ENTRY_POINT, data_context=data_context),
            tools=[find_app_extra_inst_tool],
            name="entry_point",
            streaming=False,
            model=settings.SMALL_LLM_MODEL,
        )

        corou = agent.ainvoke(state)
        result, ok = asyncio.new_event_loop().run_until_complete(
            execute_chat_with_guardrail(runnable=corou, input=state[MEMORY_KEY][-3:])
        )

        output = result["output"]

        if not ok:
            return {
                "sender": "entry_point",
                MEMORY_KEY: [AIMessage(content=output)],
                CONVERSATION_TYPE_KEY: CONV_TYPE_FAILED_GUARD,
            }

        if not isinstance(output, dict):
            try:
                trimmed_json_string = output.lstrip("`json")
                output = json.loads(trimmed_json_string)
            except json.JSONDecodeError:
                return {
                    "sender": "entry_point",
                }

        return {
            "sender": "entry_point",
            APP_ID_KEY: output.get(APP_ID_KEY),
            APP_NAME_KEY: output.get(APP_NAME_KEY),
            EXTRA_INSTRUCTIONS_KEY: output.get(EXTRA_INSTRUCTIONS_KEY),
        }

    return _epn
