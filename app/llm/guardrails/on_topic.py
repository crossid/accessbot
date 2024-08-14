from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import MessagesPlaceholder, PromptTemplate
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate
from pydantic import BaseModel, Field

from app.llm.model import create_model
from app.llm.prompts import MEMORY_KEY
from app.settings import settings


class Valid(BaseModel):
    """Is the user message valid for allowed topics"""

    is_valid: bool = Field(description="user message is valid")
    why: str = Field(description="explanation why is the user message valid or not")


_parser = PydanticOutputParser(pydantic_object=Valid)


def on_topic_guard():
    model = create_model(
        model=settings.SMALL_LLM_MODEL,
        temperature=0.3,
        streaming=False,
        name="guardrails",
    )
    allowed_topics = [
        "greeting",
        "access request",
        "work related request",
        "recommending access",
        "assistant capabilities inquiry",
        "information gathering about applications",
        "information gathering about access",
        "asking for clarification about the conversation or previous messages",
        "action repetition request",
    ]
    template = """
      You are a guardrail agent with the job of determining if the conversation is on topic.
      The topic of the conversation is, generally, requesting and granting access.
      Here are example allowed topics:
      {allowed_topics}

      The conversation is valid if the entire conversation is on topic or if the latest human message
      tries to bring it back on topic.
      Be permissive in your judgment, but don't allow general information questions or nonsense messages.
      Remember, there are other LLM agents that need to interact with the user after you.   
      
      {format_instructions}
    """
    pv = {
        "format_instructions": _parser.get_format_instructions(),
        "allowed_topics": "\n".join(f"- {topic}" for topic in allowed_topics),
    }
    prompt = PromptTemplate.from_template(template=template, partial_variables=pv)
    sys_msg = SystemMessagePromptTemplate(prompt=prompt)
    prompt = ChatPromptTemplate.from_messages(
        [sys_msg, MessagesPlaceholder(variable_name=MEMORY_KEY)]
    )

    prompt_and_model = prompt | model

    return prompt_and_model


async def topical_guardrail(user_request) -> Valid:
    guard = on_topic_guard()
    output = guard.invoke({MEMORY_KEY: user_request})
    result = _parser.invoke(output)

    return result
