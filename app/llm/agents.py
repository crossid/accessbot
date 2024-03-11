from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import MessagesPlaceholder
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.tools import Tool
from langchain_core.runnables import RunnablePassthrough
from langchain_core.utils.function_calling import convert_to_openai_function

# from ..llm.tools.retriever_tool import create_retriever_tool
from ..settings import settings
from .model import create_model, get_model_from_uri
from .prompts import MEMORY_KEY


def create_llm_function_converter(type: str):
    if type == "openai":
        return convert_to_openai_function
    else:
        raise NotImplementedError(f"LLM model {type} is not supported.")


def create_function_messages_formatter(type: str):
    if type == "openai":
        return format_to_openai_function_messages
    else:
        raise NotImplementedError(f"LLM model {type} is not supported.")


def create_agent(
    prompt: PromptTemplate,
    # data_context: dict[str, Any],
    tools: list[Tool] = [],
    name="",
    streaming=True,
) -> AgentExecutor:
    sys_msg = SystemMessagePromptTemplate(prompt=prompt)

    prompt = ChatPromptTemplate.from_messages(
        [
            sys_msg,
            MessagesPlaceholder(variable_name=MEMORY_KEY),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    model_type, _, _ = get_model_from_uri(settings.LLM_MODEL)
    model = create_model(temperature=0, streaming=streaming, name=name)

    converter = create_llm_function_converter(model_type)
    llm_with_tools = model.bind(functions=[converter(t) for t in tools])

    function_formatter = create_function_messages_formatter(model_type)

    agent = (
        RunnablePassthrough.assign(
            agent_scratchpad=lambda x: function_formatter(x["intermediate_steps"])
        )
        | prompt
        | llm_with_tools
        | OpenAIFunctionsAgentOutputParser()
    )
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor
