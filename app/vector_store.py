from urllib.parse import urlparse

from langchain_community.vectorstores.pgvector import PGVector
from langchain_community.vectorstores.sqlitevss import SQLiteVSS
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import VectorStore

from .settings import settings

ID_TRANS_TABLE = str.maketrans("-", "_")


def get_protocol(uri: str):
    parsed_url = urlparse(uri)
    protocol = parsed_url.scheme

    return protocol


# TODO embedding function should be generalized
def create_workspace_vstore(
    workspace_id: str, embedding: Embeddings, uri=settings.VSTORE_URI
) -> VectorStore:
    parsed_url = urlparse(uri)
    protocol = parsed_url.scheme

    if protocol.startswith("postgresql"):
        return PGVector(
            embedding_function=embedding,
            connection_string=uri,
            collection_name=workspace_id,
            collection_metadata={"workspace_id": workspace_id},
        )
    elif protocol == "sqlite":
        import sqlite3

        try:
            import sqlite_vss  # noqa  # pylint: disable=unused-import
        except ImportError:
            raise ImportError(
                "Could not import sqlite-vss python package. "
                "Please install it with `pip install sqlite-vss`."
            )

        db_file = parsed_url.netloc + parsed_url.path
        connection = sqlite3.connect(db_file, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.enable_load_extension(True)
        sqlite_vss.load(connection)
        connection.enable_load_extension(False)

        table = f"{workspace_id.translate(ID_TRANS_TABLE)}_data"
        return SQLiteVSS(
            connection=connection,
            table=table,
            embedding=embedding,
        )
    else:
        raise ValueError(f"{uri} vector store URI is not supported")


def delete_store(ovstore: VectorStore, uri=settings.VSTORE_URI):
    protocol = get_protocol(uri)
    if protocol.startswith("postgresql"):
        ovstore.delete_collection()


def delete_ids(ovstore: VectorStore, ids: list[str], uri=settings.VSTORE_URI) -> bool:
    protocol = get_protocol(uri)

    if protocol.startswith("postgresql"):
        """
        collecton_only is a PGVector implementation specific boolean
        For some reason, PGVector implementation doesn't take this parameter from kwargs, so we have to call it like so.
        """
        ovstore.delete(ids=ids, collection_only=True)
    else:
        """
        TODO: delete function return type is incorrect.
        Not implemented will raise an error, will not return None
        Everything else is up to the implementation, as PGVector return None on success
        """
        ovstore.delete(ids=ids)

    return True


# NOTE: this crashed if the workspace's vectorstore has no documents
def create_retriever(workspace_id: str, embedding: Embeddings) -> BaseRetriever:
    ws_ret = create_workspace_vstore(
        workspace_id=workspace_id, embedding=embedding
    ).as_retriever()
    return ws_ret

    # retrievers = []
    # weights = [1]
    # if workspace_id is not None:
    #     retrievers.append(

    #     )
    #     weights = [1]

    # ensemble_retriever = EnsembleRetriever(retrievers=retrievers, weights=weights)
    # return ensemble_retriever
