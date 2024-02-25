from urllib.parse import urlparse

from langchain_community.vectorstores import VectorStore
from langchain_community.vectorstores.pgvector import PGVector
from langchain_community.vectorstores.sqlitevss import SQLiteVSS
from langchain_core.embeddings import Embeddings

from .settings import settings

ID_TRANS_TABLE = str.maketrans("-", "_")


# TODO embedding function should be generalized
def create_org_vstore(
    org_id: str, embedding: Embeddings, uri=settings.VSTORE_URI
) -> VectorStore:
    parsed_url = urlparse(uri)
    protocol = parsed_url.scheme

    if protocol == "postgresql":
        return PGVector(
            embedding_function=embedding,
            connection_string=uri,
            collection_name=org_id,
            collection_metadata={"org_id": org_id},
        )
    elif protocol == "sqlite":
        db_file = parsed_url.netloc + parsed_url.path
        connection = SQLiteVSS.create_connection(db_file=db_file)
        print(org_id)
        table = f"{org_id.translate(ID_TRANS_TABLE)}_data"
        return SQLiteVSS(
            table=table,
            embedding=embedding,
            connection=connection,
        )
    else:
        raise ValueError(f"{uri} vector store URI is not supported")
