from typing import Optional

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.prompts import MessagesPlaceholder
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain.prompts.prompt import PromptTemplate
from langchain.tools import Tool

from ..settings import settings
from .model import create_model, get_model_from_uri
from .prompts import MEMORY_KEY


def agent_creator(type: str):
    if type == "openai" or type == "azure-openai":
        return create_openai_tools_agent
    else:
        raise NotImplementedError(f"LLM agent creator {type} is not supported.")


def create_agent(
    prompt: PromptTemplate,
    tools: list[Tool] = [],
    name="",
    streaming=True,
    model: Optional[str] = None,
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
    llm = create_model(temperature=0, streaming=streaming, name=name, model=model)

    agent = agent_creator(model_type)(llm=llm, tools=tools, prompt=prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor
