import logging

from fastapi import HTTPException, status

from app.data_fetching.iface import DataFetcherInterface
from app.data_fetching.mock import DFMockImpl
from app.data_fetching.okta import DFOktaImpl
from app.data_fetching.utils import prepare_metadata_ids_content
from app.models import Directory
from app.sql import SQLAlchemyTransactionContext
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
            docs, _ = ovstore.__list_docs__(
                workspace_id=dir.workspace_id,
                directory=dir.name,
                limit=100000,
                projection=["custom_id"],
                tx_context=tx_context,
            )
            ids_to_delete = [d.custom_id for d in docs]
            delete_ids(ovstore=ovstore, ids=ids_to_delete)
    except NotImplementedError:
        log.error(f"could not delete directory {dir.name} data before importing")
        return

    inserted_ids = ovstore.add_texts(texts=texts, metadatas=metadata, ids=ids)
    log.debug(f"inserted {len(inserted_ids)} into directory {dir.name} vector store")
