from typing import Any

from sqlalchemy import text

from app.models import Document
from app.tx import TransactionContext

collection_table_name = "langchain_pg_collection"
embedding_table_name = "langchain_pg_embedding"


def list_documents(
    workspace_id: str,
    filters: dict[str, Any] = None,
    offset=0,
    limit=10,
    tx_context: TransactionContext = None,
) -> tuple[list[Document], int]:
    stmt = text(
        f"SELECT * FROM {collection_table_name} WHERE name = :workspace_id limit 1;"
    )
    result = tx_context.connection.execute(stmt, {"workspace_id": workspace_id})
    collection = result.first()
    if collection is None:
        return [], 0

    base_count_query = text(
        f"select count(*) from {embedding_table_name} where collection_id = :collection_id;"
    )
    total_count = tx_context.connection.execute(
        base_count_query,
        {"collection_id": str(collection.uuid)},
    ).scalar_one()

    query = text(
        f"select * from {embedding_table_name} where collection_id = :collection_id order by uuid limit :limit offset :offset;"
    )

    result = tx_context.connection.execute(
        query,
        {
            "collection_id": str(collection.uuid),
            "limit": limit,
            "offset": offset,
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
