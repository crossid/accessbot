import logging

from fastapi import HTTPException, status

from app.data_fetching.iface import DataFetcherInterface
from app.data_fetching.mock import DFMockImpl
from app.data_fetching.okta import DFOktaImpl
from app.data_fetching.utils import prepare_metadata_ids_content
from app.models import Directory
from app.sql import SQLAlchemyTransactionContext
from app.utils.changes_discovery import discover_document_changes
from app.vault_utils import resolve_ws_config_secrets
from app.vector_store import delete_ids

log = logging.getLogger(__name__)


def DataFetcherFactory(dir: Directory) -> DataFetcherInterface:
    read_config = dir.read_config
    if read_config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"undefined read config on {dir.name}",
        )

    resolved_config = resolve_ws_config_secrets(
        workspace_id=dir.workspace_id, config=read_config["config"]
    )
    rctype = read_config["type"]

    match rctype:
        case "_mock_":
            return DFMockImpl()
        case "okta":
            return DFOktaImpl(workspace_id=dir.workspace_id, **resolved_config)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"no data fetching of type {rctype} defined",
    )


async def background_data_fetch(
    data_fetcher: DataFetcherInterface, ovstore, dir: Directory, **kwargs
):
    try:
        docs = await data_fetcher.fetch_content(dir_name=dir.name, **kwargs)
    except Exception as e:
        log.error(f"failed to fetch directory {dir.name} data: {str(e)}")
        return

    texts, metadata, ids = prepare_metadata_ids_content(docs)

    try:
        with SQLAlchemyTransactionContext().manage() as tx_context:
            existing_docs, _ = ovstore.__list_docs__(
                workspace_id=dir.workspace_id,
                directory=dir.name,
                limit=-1,
                projection=["custom_id", "document"],
                tx_context=tx_context,
            )

            (
                docs_to_delete,
                texts_to_insert,
                metadata_to_insert,
                ids_to_insert,
            ) = discover_document_changes(existing_docs, texts, metadata, ids)

            # Delete changed and non-existent documents
            if docs_to_delete:
                delete_ids(ovstore=ovstore, ids=docs_to_delete)
                log.debug(
                    f"Deleted {len(docs_to_delete)} changed documents from directory {dir.name}"
                )

    except NotImplementedError:
        log.error(f"could not process directory {dir.name} data")
        return

    # Insert new or changed documents
    if len(texts_to_insert) > 0:
        inserted_ids = ovstore.add_texts(
            texts=texts_to_insert, metadatas=metadata_to_insert, ids=ids_to_insert
        )
        log.debug(
            f"Inserted {len(inserted_ids)} new or changed documents into directory {dir.name} vector store"
        )
    else:
        log.debug(f"No new or changed documents to insert for directory {dir.name}")
