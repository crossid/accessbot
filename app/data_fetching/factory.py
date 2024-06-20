import logging

from fastapi import HTTPException, status

from app.data_fetching.iface import DataFetcherInterface
from app.data_fetching.mock import DFMockImpl
from app.data_fetching.okta import DFOktaImpl
from app.data_fetching.utils import prepare_metadata_ids_content
from app.models import Directory
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
            return DFOktaImpl(**resolved_config)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"no data fetching of type {rctype} defined",
    )


async def background_data_fetch(
    data_fetcher: DataFetcherInterface, ovstore, dir: Directory
):
    try:
        docs = await data_fetcher.fetch_content(dir_name=dir.name)
        for doc in docs:
            doc.external_id = dir.name
    except Exception as e:
        log.error(f"failed to fetch directory {dir.name} data: {str(e)}")
        return

    texts, metadata, ids = prepare_metadata_ids_content(docs)
    try:
        delete_ids(ovstore=ovstore, ids=[dir.name])
    except NotImplementedError:
        log.error(f"could not delete directory {dir.name} data before importing")
        return

    inserted_ids = ovstore.add_texts(texts=texts, metadatas=metadata, ids=ids)
    log.debug(f"inserted {len(inserted_ids)} into directory {dir.name} vector store")
