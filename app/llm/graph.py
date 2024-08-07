import json
import operator
from typing import Annotated, Any, Callable, Dict, Optional, Sequence, TypedDict

from langchain.prompts.prompt import PromptTemplate
from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables.base import RunnableLike
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolExecutor, ToolInvocation

from app.llm.tools.create_ticket_for_role_request_tool import create_request_roles_tool
from app.llm.tools.deny_access_tool import create_deny_provision_tool
from app.llm.tools.provision_role_tool import create_provision_role_tool
from app.llm.tools.retriever_tool import create_retriever_tool

from .nodes import (
    CONV_TYPE_DATA_OWNER,
    CONV_TYPE_FAILED_GUARD,
    CONV_TYPE_INFO,
    CONVERSATION_TYPE_KEY,
    DATA_OWNER_AGENT_NODE,
    INFORMATION_AGENT_NAME,
    RECOMMENDER_AGENT_NAME,
    create_data_owner_node,
    create_info_gatherer_node,
    create_recommendation_node,
    entry_point_node,
)
from .prompts import MEMORY_KEY, WS_ID_KEY


class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    sender: str
    conv_type: str
    app_id: str
    app_name: str
    extra_instructions: str


def create_tool_node(tools, ws_id):
    def tool_node(state):
        app_id = state.get("app_id", None)
        if app_id is not None:
            prt = create_provision_role_tool(app_id=app_id, ws_id=ws_id)
            if prt is not None:
                tools.append(prt)

            dpt = create_deny_provision_tool(app_id=app_id, ws_id=ws_id)
            if dpt is not None:
                tools.append(dpt)

            crrt = create_request_roles_tool(app_id=app_id, ws_id=ws_id)
            if crrt is not None:
                tools.append(crrt)

        """This runs tools in the graph
        It takes in an agent action and calls that tool and returns the result."""

        tool_executor = ToolExecutor(tools)

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
        # We use the response to create a ToolMessage
        tool_message = ToolMessage(
            content=f"{tool_name} response: {str(response)}", name=action.tool
        )

        # We return a list, because this will get added to the existing list
        return {"messages": [tool_message]}

    return tool_node


# Either agent can decide to end
def router(state):
    # This is the router
    messages = state[MEMORY_KEY]
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

    def __init__(self, name: str, action: RunnableLike):
        self.name = name
        self.action = action


class _Condition_Edge:
    start_key: str
    condition: Callable[..., str]
    conditional_edge_mapping: Optional[Dict[str, str]] = None

    def __init__(
        self,
        start_key: str,
        condition: Callable[..., str],
        conditional_edge_mapping: Optional[Dict[str, str]] = None,
    ):
        self.start_key = start_key
        self.condition = condition
        self.conditional_edge_mapping = conditional_edge_mapping


def base_nodes(
    base_tools,
    ret_tool,
    data_context: dict[str, Any] = {},
) -> list[_Node]:
    return [
        _Node(name="entry_point", action=entry_point_node(data_context=data_context)),
        _Node(
            name=DATA_OWNER_AGENT_NODE,
            action=create_data_owner_node(data_context=data_context),
        ),
        _Node(
            name=INFORMATION_AGENT_NAME,
            action=create_info_gatherer_node(data_context=data_context),
        ),
        _Node(
            name=RECOMMENDER_AGENT_NAME,
            action=create_recommendation_node(
                data_context=data_context, ret_tool=ret_tool
            ),
        ),
        _Node(
            name="call_tool",
            action=create_tool_node(
                tools=base_tools + [ret_tool], ws_id=data_context.get(WS_ID_KEY)
            ),
        ),
    ]


def base_edges() -> list[_Condition_Edge]:
    return [
        _Condition_Edge(
            start_key="entry_point",
            condition=lambda x: x[CONVERSATION_TYPE_KEY],
            conditional_edge_mapping={
                CONV_TYPE_INFO: INFORMATION_AGENT_NAME,
                CONV_TYPE_DATA_OWNER: DATA_OWNER_AGENT_NODE,
                CONV_TYPE_FAILED_GUARD: END,
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
    checkpointer: BaseCheckpointSaver = None,
):
    ret_tool = create_retriever_tool(
        retriever=retriever,
        name="recommend_access",
        description="Searches and returns documents in order to recommend access to the user.",
        document_prompt=PromptTemplate.from_template(
            "{page_content}\n**directory**: {directory}"
        ),
    )

    # add nodes
    workflow = StateGraph(state)

    if nodes is None:
        nodes = base_nodes(
            base_tools=tools, data_context=data_context, ret_tool=ret_tool
        )

    for node in nodes:
        workflow.add_node(node.name, node.action)

    # add edges
    if edges is None:
        edges = base_edges()

    for edge in edges:
        workflow.add_conditional_edges(
            edge.start_key,
            edge.condition,
            edge.conditional_edge_mapping,
        )

    workflow.set_entry_point(entry_point_node_name)

    graph = workflow.compile(checkpointer=checkpointer)

    return graph
