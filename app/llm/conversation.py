# from langchain.globals import set_debug

from app.embeddings import create_embedding
from app.llm.agents import create_agent
from app.llm.prompts import (
    ORGID_KEY,
    REQUEST_ID_KEY,
    USERNAME_KEY,
)
from app.models import AccessRequest, StatusEnum
from app.vector_store import create_retriever

from .prompts import prompt_facade

# set_debug(True)


def create_agent_for_access_request_conversation(
    access_request: AccessRequest, streaming=True
):
    embedding = create_embedding()
    retriever = create_retriever(org_id=access_request.org_id, embedding=embedding)

    prompt = None
    if access_request.status != StatusEnum.active.value:
        prompt = prompt_facade.get("generic_recommendation")
    else:
        raise ValueError("Invalid status for access request")

    data_context = {
        USERNAME_KEY: lambda x: x[USERNAME_KEY],
        ORGID_KEY: lambda x: x[ORGID_KEY],
        REQUEST_ID_KEY: lambda x: x[REQUEST_ID_KEY],
    }

    agent_executor = create_agent(
        retriever=retriever,
        prompt=prompt,
        data_context=data_context,
        tools=[],
        streaming=streaming,
    )

    return agent_executor


def sse_client_transformer(output: str) -> str:
    event_str = f"event: chat-message\ndata: {output}\n\n"
    return event_str
