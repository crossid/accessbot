from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import MessagesPlaceholder, PromptTemplate
from langchain.prompts.chat import ChatPromptTemplate, SystemMessagePromptTemplate
from pydantic import BaseModel, Field

from app.llm.model import create_model
from app.llm.prompts import MEMORY_KEY
from app.settings import settings


class Valid(BaseModel):
    """Is the user message valid for topics"""

    is_valid: bool = Field(description="user message is valid")


_parser = PydanticOutputParser(pydantic_object=Valid)


def on_topic_guard():
    model = create_model(
        model=settings.SMALL_LLM_MODEL,
        temperature=0.2,
        streaming=False,
        name="guardrails",
    )
    allowed_topics = [
        "greeting",
        "access request",
        "recommending access",
        "information about applications",
    ]
    template = """
      Your job is to determine if the user's input is on topic
      allowed topics are: {allowed_topics}
      {format_instructions}
    """
    pv = {
        "format_instructions": _parser.get_format_instructions(),
        "allowed_topics": ",".join(allowed_topics),
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
