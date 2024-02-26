from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.settings import settings


def create_embedding(embedding_type: str = settings.VSTORE_EMBEDDING) -> Embeddings:
    if embedding_type == "openai":
        return OpenAIEmbeddings()
    elif embedding_type == "sentence_transformer":
        return SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    else:
        raise ValueError(f"{embedding_type} is not supported")
