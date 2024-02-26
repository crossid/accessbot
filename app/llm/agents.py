from typing import Any

from langchain.agents import AgentExecutor
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import MessagesPlaceholder
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.tools import Tool
from langchain_core.retrievers import BaseRetriever
from langchain_core.utils.function_calling import convert_to_openai_function

from app.llm.model import create_model, get_model_from_uri
from app.llm.prompts import MEMORY_KEY
from app.settings import settings


def create_llm_function_converter(type: str):
    if type == "openai":
        return convert_to_openai_function
    else:
        raise NotImplementedError(f"LLM model {type} is not supported.")


def crete_function_messages_formatter(type: str):
    if type == "openai":
        return format_to_openai_function_messages
    else:
        raise NotImplementedError(f"LLM model {type} is not supported.")


def create_agent(
    retriever: BaseRetriever,
    prompt: PromptTemplate,
    data_context: dict[str, Any],
    tools: list[Tool] = [],
    streaming=True,
) -> AgentExecutor:
    ret_tool = create_retriever_tool(
        retriever,
        "recommend_and_grant_access",
        "Searches and returns documents, recommends and grant access to the user.",
    )

    tools.append(ret_tool)
    sys_msg = SystemMessagePromptTemplate(prompt=prompt)

    prompt = ChatPromptTemplate.from_messages(
        [
            sys_msg,
            MessagesPlaceholder(variable_name=MEMORY_KEY),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    model_type, _, _ = get_model_from_uri(settings.LLM_MODEL)
    model = create_model(temperature=0, streaming=streaming)

    converter = create_llm_function_converter(model_type)
    llm_with_tools = model.bind(functions=[converter(t) for t in tools])

    function_formatter = crete_function_messages_formatter(model_type)

    ctx = data_context | {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: function_formatter(x["intermediate_steps"]),
        MEMORY_KEY: lambda x: x[MEMORY_KEY],
    }

    agent = ctx | prompt | llm_with_tools | OpenAIFunctionsAgentOutputParser()
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor
