import json
import operator
from typing import Annotated, Any, Callable, Dict, Optional, Sequence, TypedDict

from langchain.agents.agent_toolkits import create_retriever_tool
from langchain.prompts.prompt import PromptTemplate
from langchain_core.messages import (
    BaseMessage,
    FunctionMessage,
    HumanMessage,
)
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables.base import RunnableLike
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.prebuilt.tool_executor import ToolExecutor, ToolInvocation

from .nodes import (
    CONV_TYPE_DATA_OWNER,
    CONV_TYPE_INFO,
    DATA_OWNER_AGENT_NODE,
    INFORMATION_AGENT_NAME,
    RECOMMENDER_AGENT_NAME,
    create_data_owner_node,
    create_info_gatherer_node,
    create_recommendation_node,
)


class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    sender: str
    conv_type: str


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


def create_tool_node(tool_executor):
    def tool_node(state):
        """This runs tools in the graph

        It takes in an agent action and calls that tool and returns the result."""
        messages = state["messages"]
        # Based on the continue condition
        # we know the last message involves a function call
        last_message = messages[-1]
        # We construct an ToolInvocation from the function_call
        tool_input = json.loads(
            last_message.additional_kwargs["function_call"]["arguments"]
        )
        # We can pass single-arg inputs by value
        if len(tool_input) == 1 and "__arg1" in tool_input:
            tool_input = next(iter(tool_input.values()))
        tool_name = last_message.additional_kwargs["function_call"]["name"]
        action = ToolInvocation(
            tool=tool_name,
            tool_input=tool_input,
        )
        # We call the tool_executor and get back a response
        response = tool_executor.invoke(action)
        # We use the response to create a FunctionMessage
        function_message = FunctionMessage(
            content=f"{tool_name} response: {str(response)}", name=action.tool
        )
        # We return a list, because this will get added to the existing list
        return {"messages": [function_message]}

    return tool_node


# Either agent can decide to end
def router(state):
    # This is the router
    messages = state["messages"]
    last_message = messages[-1]

    if "function_call" in last_message.additional_kwargs:
        # The previous agent is invoking a tool
        return "call_tool"

    if RECOMMENDER_AGENT_NAME not in last_message.content:
        # Any agent decided the work is done
        return "end"

    return "continue"


class _Node:
    name: str
    action: RunnableLike


class _Condition_Edge:
    start_key: str
    condition: Callable[..., str]
    conditional_edge_mapping: Optional[Dict[str, str]] = None


def entry_point_node(state):
    return {
        "messages": state["messages"],
        "conv_type": state["conv_type"],
        "sender": "entry_point",
    }


def base_nodes(
    tool_executor,
    ret_tool,
    data_context: dict[str, Any] = {},
) -> list[_Node]:
    return [
        _Node(name="entry_point", action=entry_point_node),
        _Node(name=DATA_OWNER_AGENT_NODE, action=create_data_owner_node(data_context)),
        _Node(
            name=INFORMATION_AGENT_NAME, action=create_info_gatherer_node(data_context)
        ),
        _Node(
            name=RECOMMENDER_AGENT_NAME,
            action=create_recommendation_node(data_context, ret_tool),
        ),
        _Node(name="call_tool", action=create_tool_node(tool_executor=tool_executor)),
    ]


def base_edges() -> list[_Condition_Edge]:
    return [
        _Condition_Edge(
            start_key="entry_point",
            condition=lambda x: x["conv_type"],
            conditional_edge_mapping={
                CONV_TYPE_INFO: INFORMATION_AGENT_NAME,
                CONV_TYPE_DATA_OWNER: DATA_OWNER_AGENT_NODE,
            },
        ),
        _Condition_Edge(
            start_key=DATA_OWNER_AGENT_NODE,
            condition=router,
            conditional_edge_mapping={
                "continue": RECOMMENDER_AGENT_NAME,
                "call_tool": "call_tool",
                "end": END,
            },
        ),
        _Condition_Edge(
            start_key=INFORMATION_AGENT_NAME,
            condition=router,
            conditional_edge_mapping={
                "continue": RECOMMENDER_AGENT_NAME,
                "call_tool": "call_tool",
                "end": END,
            },
        ),
        _Condition_Edge(
            start_key=RECOMMENDER_AGENT_NAME,
            condition=lambda state: "function_call"
            if "function_call" in state["messages"][-1].additional_kwargs
            else state["sender"],
            conditional_edge_mapping={
                INFORMATION_AGENT_NAME: INFORMATION_AGENT_NAME,
                DATA_OWNER_AGENT_NODE: DATA_OWNER_AGENT_NODE,
                "call_tool": "call_tool",
            },
        ),
        _Condition_Edge(
            start_key="call_tool",
            condition=lambda x: x["sender"],
            conditional_edge_mapping={
                INFORMATION_AGENT_NAME: INFORMATION_AGENT_NAME,
                RECOMMENDER_AGENT_NAME: RECOMMENDER_AGENT_NAME,
            },
        ),
    ]


def create_graph(
    tools: list[BaseTool],
    retriever: BaseRetriever,
    data_context: dict[str, Any] = {},
    state=GraphState,
    nodes: list[_Node] = None,
    edges: list[_Condition_Edge] = None,
    entry_point_node_name="entry_point",
):
    ret_tool = create_retriever_tool(
        retriever=retriever,
        name="recommend_access",
        description="Searches and returns documents in order to recommend access to the user.",
        document_prompt=PromptTemplate.from_template(
            "{page_content}\n**directory**: {directory}"
        ),
    )

    tool_executor = ToolExecutor(tools.append(ret_tool))
    # add nodes
    workflow = StateGraph(state)

    if nodes is None:
        nodes = base_nodes(
            tool_executor=tool_executor, data_context=data_context, ret_tool=ret_tool
        )

    for node in nodes:
        workflow.add_node(node.name, node.action)

    # add edges
    if edges is None:
        edges = base_edges()

    for edge in edges:
        workflow.add_conditional_edges(
            start_key=edge.start_key,
            condition=edge.condition,
            conditional_edge_mapping=edge.conditional_edge_mapping,
        )

    workflow.set_entry_point(entry_point_node_name)
    graph = workflow.compile()

    return graph
