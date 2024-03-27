import functools

from langchain_core.messages import (
    FunctionMessage,
    HumanMessage,
)

from .agents import create_agent

INFORMATION_AGENT_NAME = "Information"
RECOMMENDER_AGENT_NAME = "Recommender"
DATA_OWNER_AGENT_NODE = "Data Owner"
CONV_TYPE_DATA_OWNER = "data_owner"
CONV_TYPE_INFO = "info"


def agent_node(state, agent, name):
    result = agent.invoke(state)
    # We convert the agent output into a format that is suitable to append to the global state
    if isinstance(result, FunctionMessage):
        pass
    else:
        result = HumanMessage(content=result["output"], name=name)

    return {
        "messages": [result],
        "conv_type": state["conv_type"],
        # Since we have a strict workflow, we can
        # track the sender so we know who to pass to next.
        "sender": name if name != RECOMMENDER_AGENT_NAME else state["sender"],
    }


def create_data_owner_node(data_context):
    def data_owner_node(state):
        print("data_owner_node")
        return {
            "messages": [HumanMessage(content="I am the data owner node")],
            "conv_type": state["conv_type"],
            "sender": DATA_OWNER_AGENT_NODE,
        }

    return data_owner_node


def create_info_agent():
    tools = []
    agent = create_agent(prompt="", tools=tools)
    return agent


def create_info_gatherer_node(data_context):
    info_agent = create_info_agent()

    info_gatherer_node = functools.partial(
        agent_node, agent=info_agent, name=INFORMATION_AGENT_NAME
    )

    return info_gatherer_node


def create_recommend_agent(data_context, ret_tool):
    agent = create_agent(prompt="", data_context={}, tools=[ret_tool])
    return agent


def create_recommendation_node():
    rec_agent = create_recommend_agent()
    recommendation_node = functools.partial(
        agent_node, agent=rec_agent, name=RECOMMENDER_AGENT_NAME
    )

    return recommendation_node
