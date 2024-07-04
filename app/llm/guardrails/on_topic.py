from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

from app.llm.model import create_model
from app.settings import settings


class Valid(BaseModel):
    """Is the user message valid for topics"""

    is_valid: bool = Field(description="user message is valid")


_parser = PydanticOutputParser(pydantic_object=Valid)


def on_topic_guard():
    model = create_model(
        model=settings.GUARDRAILS_LLM_MODEL,
        temperature=0.2,
        streaming=False,
        name="guardrails",
    )
    allowed_topics = [
        "greeting",
        "yes or no answers",
        "access request",
        "recommending access",
        "information about applications",
    ]
    template = f"""
      Your job is to determine if the user's input is on topic
      allowed topics are: {','.join(allowed_topics)}
    """
    prompt = PromptTemplate(
        template="{template}.\n{format_instructions}\n{query}\n",
        input_variables=["query"],
        partial_variables={
            "format_instructions": _parser.get_format_instructions(),
            "template": template,
        },
    )

    prompt_and_model = prompt | model

    return prompt_and_model


async def topical_guardrail(user_request) -> Valid:
    guard = on_topic_guard()
    output = guard.invoke({"query": user_request})
    result = _parser.invoke(output)

    return result
