import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ValidationError

from app.models import Document, PaginatedListBase, Workspace
from app.services import pagination_params
from app.sql import SQLAlchemyTransactionContext

from ..auth import get_current_workspace, setup_workspace_vstore
from ..id import generate
from ..settings import settings
from ..vector_store import delete_ids, get_protocol

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/content",
    tags=["content"],
)


class Doc(BaseModel):
    id: Optional[str] = None
    apps: list[str]
    directory: str
    content: str
    external_id: Optional[str]


class AddContentBody(BaseModel):
    docs: List[Doc]


class AddContentResponse(BaseModel):
    ok: bool
    ids: List[str]


def prepare_metadata_ids_content(docs: List[Doc]):
    metadatas = []
    ids = []
    content = []

    for doc in docs:
        dmeta = {"directory": doc.directory, "app": doc.apps}
        metadatas.append(dmeta)
        ids.append(doc.external_id if doc.external_id is not None else generate())
        content.append(doc.content)

    return content, metadatas, ids


@router.post("", response_model=AddContentResponse)
async def add(body: AddContentBody, ovstore=Depends(setup_workspace_vstore)):
    texts, metadata, ids = prepare_metadata_ids_content(body.docs)
    inserted_ids = ovstore.add_texts(texts=texts, metadatas=metadata, ids=ids)
    # convert ids to strings (SQLite returns int)
    inserted_ids = [str(i) for i in inserted_ids]
    return AddContentResponse(ok=True, ids=inserted_ids)


class RemoveContentBody(BaseModel):
    ids: List[str]


@router.post("/.delete", status_code=status.HTTP_204_NO_CONTENT)
async def remove(body: RemoveContentBody, ovstore=Depends(setup_workspace_vstore)):
    try:
        delete_ids(ovstore=ovstore, ids=body.ids)
    except NotImplementedError:
        raise HTTPException(
            detail=f"delete not implemented for type {get_protocol(settings.VSTORE_URI)}",
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
        )
    except Exception as e:
        raise HTTPException(
            detail=f"error while deleting ids: [{e}]",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class DocumentList(PaginatedListBase):
    items: List[Doc]


def store_doc_to_api_doc(doc: Document) -> Doc:
    return Doc(
        id=str(doc.uuid),
        external_id=doc.custom_id,
        content=doc.document,
        apps=doc.cmetadata.get("app", []),
        directory=doc.cmetadata.get("directory", ""),
    )


@router.get("", response_model=DocumentList, response_model_exclude_none=True)
async def list(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    directory: str | None = None,
    app_names: List[str] | None = Query(None),
    list_params: dict = Depends(pagination_params),
    ovstore=Depends(setup_workspace_vstore),
):
    limit = list_params.get("limit", 10)
    offset = list_params.get("offset", 0)
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            docs, total = ovstore.__list_docs__(
                workspace_id=workspace.id,
                offset=offset,
                limit=limit,
                tx_context=tx_context,
                directory=directory,
                app_names=app_names,
            )
            return DocumentList(
                items=[store_doc_to_api_doc(doc) for doc in docs],
                offset=offset,
                total=total,
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
