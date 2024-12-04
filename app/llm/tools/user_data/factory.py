import logging
from datetime import datetime
from typing import List

from app.llm.tools.user_data.iface import UserDataInterface
from app.llm.tools.user_data.mock import MockImpl
from app.llm.tools.user_data.okta import OktaUserDataImpl
from app.llm.tools.user_data.webhook import WebhookImpl
from app.models import Directory, Workspace
from app.sql import SQLAlchemyTransactionContext
from app.utils.changes_discovery import discover_document_changes
from app.utils.strings import dict_to_md
from app.vault_utils import resolve_ws_config_secrets
from app.vector_store import delete_ids

log = logging.getLogger(__name__)


def GetUserDataFactory(workspace: Workspace, directory: Directory) -> UserDataInterface:
    if directory.read_config is None:
        return None

    read_type = directory.read_config["type"]
    read_config = directory.read_config["config"]
    resolved_config = resolve_ws_config_secrets(
        workspace_id=workspace.id, config=read_config
    )

    match read_type:
        case "webhook":
            return WebhookImpl(**resolved_config)
        case "okta":
            return OktaUserDataImpl(**resolved_config)
        case "_mock_":
            return MockImpl(**resolved_config)

    raise ValueError(
        f"could not instantiate get user data factory for type: {read_type}"
    )


def prepare_user_docs(users: List[dict], dir_name: str):
    texts = []
    metadatas = []
    ids = []

    for user in users:
        text = dict_to_md(user)
        texts.append(text)
        ids.append(user["id"])
        metadata = {
            "email": user.get("email", ""),
            "type": "user",
            "created_at": datetime.now().isoformat(),
            "display_name": user.get("display_name", user.get("displayName", "")),
            "directory": dir_name,
        }
        metadatas.append(metadata)

    return texts, metadatas, ids


async def background_users_fetch(
    data_fetcher: UserDataInterface, ovstore, dir: Directory, **kwargs
):
    try:
        docs = await data_fetcher.list_users_data(**kwargs)
    except Exception as e:
        log.error(f"failed to fetch directory {dir.name} data: {str(e)}")
        return

    texts, metadata, ids = prepare_user_docs(users=docs, dir_name=dir.name)

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
