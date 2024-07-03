from typing import List, Optional

from sqlalchemy import text

from app.models import Document
from app.sql import SQLAlchemyTransactionContext

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


def record_to_doc(record):
    cmetadata = {}
    if hasattr(record, "cmetadata"):
        cmetadata = record.cmetadata
    else:
        if hasattr(record, "app"):
            cmetadata["app"] = record.app
        if hasattr(record, "directory"):
            cmetadata["directory"] = record.directory

    doc = Document(
        collection_id=str(record.collection_id)
        if hasattr(record, "collection_id")
        else "",
        uuid=str(record.uuid) if hasattr(record, "uuid") else "",
        custom_id=str(record.custom_id) if hasattr(record, "custom_id") else "",
        cmetadata=cmetadata,
        document=record.document if hasattr(record, "document") else "",
    )
    return doc


def create_projection(proj: Optional[List[str]] = []):
    if proj is None or len(proj) == 0:
        return "*"

    translate = {
        "id": "uuid",
        "external_id": "custom_id",
        "apps": "cmetadata -> 'app' as app",
        "directory": "cmetadata -> 'directory' as directory",
        "content": "document",
    }

    to_get = {translate[item] for item in proj if item in translate}
    return ", ".join(to_get)


def get_document(
    workspace_id: str,
    id: Optional[str] = "",
    external_id: Optional[str] = "",
    projection: Optional[List[str]] = [],
    tx_context: SQLAlchemyTransactionContext = None,
):
    if id == "" and external_id == "":
        return None

    stmt = text(
        f"SELECT * FROM {collection_table_name} WHERE name = :workspace_id limit 1;"
    )
    result = tx_context.connection.execute(stmt, {"workspace_id": workspace_id})
    collection = result.first()
    if collection is None:
        return None

    proj = create_projection(proj=projection)
    query = text(
        f"select {proj} from {embedding_table_name} where collection_id = :collection_id and (uuid::text = :id or custom_id = :external_id) limit 1;"
    )

    result = tx_context.connection.execute(
        query,
        {"collection_id": str(collection.uuid), "id": id, "external_id": external_id},
    )
    record = result.first()
    if record is None:
        return None

    return record_to_doc(record)


def list_documents(
    workspace_id: str,
    app_names: Optional[List[str]] = None,
    directory: Optional[str] = None,
    offset=0,
    limit=10,
    projection: Optional[List[str]] = [],
    tx_context: SQLAlchemyTransactionContext = None,
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

    proj = create_projection(proj=projection)
    query = text(
        f"select {proj} from {embedding_table_name} where {filters} order by uuid limit :limit offset :offset;"
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
        doc = record_to_doc(record=record)
        docs.append(doc)

    return docs, total_count
