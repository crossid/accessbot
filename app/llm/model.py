from urllib.parse import parse_qs, urlparse

from langchain_core.language_models.chat_models import (
    BaseChatModel,
)
from langchain_openai import ChatOpenAI

from ..settings import settings
from .fake_model import FakeChatOpenAI

LLM_ALLOWED_ARGS = {
    "openai": ["temperature", "streaming"],
    "fake": ["responses", "sleep"],
}


def get_model_from_uri(uri: str) -> tuple[str, str, dict[str, str]]:
    parsed_url = urlparse(uri)
    protocol = parsed_url.scheme
    qp = parse_qs(parsed_url.query)

    return [protocol, parsed_url.netloc, qp]


def create_model(**args) -> BaseChatModel:
    # TODO convert qp as model args
    type, model, qp = get_model_from_uri(settings.LLM_MODEL)
    if type == "fake":
        filtered_args = {
            key: value for key, value in args.items() if key in LLM_ALLOWED_ARGS["fake"]
        }

        return FakeChatOpenAI(**filtered_args)
    elif type.startswith("openai"):
        args["model"] = model
        if "temperature" not in args:
            args["temperature"] = 0.9
        args["streaming"] = True
        filtered_args = {
            key: value
            for key, value in args.items()
            if key in LLM_ALLOWED_ARGS["openai"]
        }
        return ChatOpenAI(**filtered_args)
    else:
        raise ValueError(f"LLM_MODEL env var with type '{type}' is not supported")
