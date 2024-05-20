from typing import List, Optional

from sqlalchemy import text

from app.models import Document
from app.tx import TransactionContext

collection_table_name = "langchain_pg_collection"
embedding_table_name = "langchain_pg_embedding"


def prepare_where(directory: Optional[str], app_names: Optional[List[str]]):
    base_where = "collection_id = :collection_id"
    if directory is not None:
        base_where += " and cmetadata::jsonb -> 'directory' = :directory"

    if app_names is not None:
        apps_str = ", ".join(
            ["'[\"{name}\"]'::jsonb".format(name=n) for n in app_names]
        )
        base_where += f" and cmetadata::jsonb -> 'app' @> ANY(ARRAY[{apps_str}])"

    return base_where


def list_documents(
    workspace_id: str,
    app_names: Optional[List[str]] = None,
    directory: Optional[str] = None,
    offset=0,
    limit=10,
    tx_context: TransactionContext = None,
) -> tuple[List[Document], int]:
    stmt = text(
        f"SELECT * FROM {collection_table_name} WHERE name = :workspace_id limit 1;"
    )
    result = tx_context.connection.execute(stmt, {"workspace_id": workspace_id})
    collection = result.first()
    if collection is None:
        return [], 0

    filters = prepare_where(directory=directory, app_names=app_names)
    base_count_query = text(
        f"select count(*) from {embedding_table_name} where {filters}"
    )
    total_count = tx_context.connection.execute(
        base_count_query,
        {"collection_id": str(collection.uuid), "directory": f'"{directory}"'},
    ).scalar_one()

    query = text(
        f"select * from {embedding_table_name} where {filters} order by uuid limit :limit offset :offset;"
    )

    result = tx_context.connection.execute(
        query,
        {
            "collection_id": str(collection.uuid),
            "limit": limit,
            "offset": offset,
            "directory": f'"{directory}"',
        },
    )
    docs = []
    for record in result:
        doc = Document(
            uuid=str(record.uuid),
            custom_id=str(record.custom_id),
            cmetadata=record.cmetadata,
            document=record.document,
            collection_id=str(record.collection_id),
        )
        docs.append(doc)

    return docs, total_count
