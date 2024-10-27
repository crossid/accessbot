from functools import partial
from typing import Optional

from langchain.tools import StructuredTool
from langchain_core.callbacks.manager import (
    Callbacks,
)
from langchain_core.prompts import BasePromptTemplate, PromptTemplate, format_document
from langchain_core.vectorstores import VectorStoreRetriever
from pydantic import BaseModel, Field


class RetrieverInput(BaseModel):
    """Input to the retriever."""

    query: str = Field(description="query to look up in retriever")
    app_name: str = Field(description="name of the application the user needs access")


"""
a second option is to use Runtime Configuration
to change the search kwargs
https://python.langchain.com/docs/modules/data_connection/retrievers/ensemble/#runtime-configuration
"""


def _get_relevant_documents(
    query: str,
    app_name: str,
    retriever: VectorStoreRetriever,
    document_prompt: BasePromptTemplate,
    document_separator: str,
    callbacks: Callbacks = None,
) -> str:
    retriever.search_kwargs.update({"filter": {"app": {"contains": app_name.lower()}}})
    docs = retriever.invoke(query, config={"callbacks": callbacks})
    return document_separator.join(
        format_document(doc, document_prompt) for doc in docs
    )


async def _aget_relevant_documents(
    query: str,
    app_name: str,
    retriever: VectorStoreRetriever,
    document_prompt: BasePromptTemplate,
    document_separator: str,
    callbacks: Callbacks = None,
) -> str:
    retriever.search_kwargs.update({"filter": {"app": {"contains": app_name.lower()}}})
    docs = await retriever.ainvoke(query, config={"callbacks": callbacks})
    formatted_docs = [format_document(doc, document_prompt) for doc in docs]
    return document_separator.join(formatted_docs)


def create_retriever_tool(
    retriever: VectorStoreRetriever,
    name: str,
    description: str,
    *,
    document_prompt: Optional[BasePromptTemplate] = None,
    document_separator: str = "\n\n",
) -> StructuredTool:
    """Create a tool to do retrieval of documents.

    Args:
        retriever: The retriever to use for the retrieval
        name: The name for the tool. This will be passed to the language model,
            so should be unique and somewhat descriptive.
        description: The description for the tool. This will be passed to the language
            model, so should be descriptive.

    Returns:
        Tool class to pass to an agent
    """
    document_prompt = document_prompt or PromptTemplate.from_template(
        "{page_content}\n**directory**: {directory}"
    )
    func = partial(
        _get_relevant_documents,
        retriever=retriever,
        document_prompt=document_prompt,
        document_separator=document_separator,
    )
    afunc = partial(
        _aget_relevant_documents,
        retriever=retriever,
        document_prompt=document_prompt,
        document_separator=document_separator,
    )
    return StructuredTool.from_function(
        name=name,
        description=description,
        func=func,
        coroutine=afunc,
        args_schema=RetrieverInput,
    )
