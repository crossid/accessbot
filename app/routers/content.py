import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ValidationError

from app.authz import Permissions, is_admin_or_has_scopes
from app.data_fetching.utils import Doc, prepare_metadata_ids_content
from app.models import Document, PaginatedListBase, Workspace
from app.services import pagination_params
from app.sql import SQLAlchemyTransactionContext, doc_store_engine

from ..auth import get_current_workspace, setup_workspace_vstore
from ..settings import settings
from ..vector_store import delete_ids, get_protocol

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/content",
    tags=["content"],
)


class AddContentBody(BaseModel):
    docs: List[Doc]


class AddContentResponse(BaseModel):
    ok: bool
    ids: List[str]


@router.put("", response_model=AddContentResponse)
async def update(
    body: AddContentBody,
    ovstore=Depends(setup_workspace_vstore),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_CONTENT.value])),
):
    texts, metadata, ids = prepare_metadata_ids_content(body.docs)
    try:
        delete_ids(ovstore=ovstore, ids=ids)
    except NotImplementedError:
        raise HTTPException(
            detail=f"delete not implemented for type {get_protocol(settings.VSTORE_URI)}",
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
        )

    inserted_ids = ovstore.add_texts(texts=texts, metadatas=metadata, ids=ids)
    # convert ids to strings (SQLite returns int)
    inserted_ids = [str(i) for i in inserted_ids]
    return AddContentResponse(ok=True, ids=inserted_ids)


@router.post("", response_model=AddContentResponse)
async def add(
    body: AddContentBody,
    ovstore=Depends(setup_workspace_vstore),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_CONTENT.value])),
):
    texts, metadata, ids = prepare_metadata_ids_content(body.docs)
    inserted_ids = ovstore.add_texts(texts=texts, metadatas=metadata, ids=ids)
    # convert ids to strings (SQLite returns int)
    inserted_ids = [str(i) for i in inserted_ids]
    return AddContentResponse(ok=True, ids=inserted_ids)


class RemoveContentBody(BaseModel):
    ids: List[str]


@router.post("/.delete", status_code=status.HTTP_204_NO_CONTENT)
async def remove(
    body: RemoveContentBody,
    ovstore=Depends(setup_workspace_vstore),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.DELETE_CONTENT.value])),
):
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
        id=doc.uuid if doc.uuid != "" else None,
        external_id=doc.custom_id if doc.custom_id != "" else None,
        content=doc.document if doc.document != "" else None,
        apps=doc.cmetadata.get("app", None),
        directory=doc.cmetadata.get("directory", None),
    )


@router.get("/{id}", response_model=Doc, response_model_exclude_none=True)
async def get(
    id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    projection: List[str] | None = Query(None),
    ovstore=Depends(setup_workspace_vstore),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.READ_CONTENT.value])),
):
    with SQLAlchemyTransactionContext(engine=doc_store_engine).manage() as tx_context:
        try:
            doc = ovstore.__get_doc__(
                workspace_id=workspace.id,
                id=id,
                external_id=id,
                tx_context=tx_context,
                projection=projection,
            )
            if doc is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="not found"
                )

            return store_doc_to_api_doc(doc)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


@router.get("", response_model=DocumentList, response_model_exclude_none=True)
async def list(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    directory: str | None = Query(None),
    app_names: List[str] | None = Query(None),
    list_params: dict = Depends(pagination_params),
    projection: List[str] | None = Query(None),
    ovstore=Depends(setup_workspace_vstore),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.READ_CONTENT.value])),
):
    limit = list_params.get("limit", 10)
    offset = list_params.get("offset", 0)
    with SQLAlchemyTransactionContext(engine=doc_store_engine).manage() as tx_context:
        try:
            docs, total = ovstore.__list_docs__(
                workspace_id=workspace.id,
                offset=offset,
                limit=limit,
                tx_context=tx_context,
                directory=directory,
                app_names=app_names,
                projection=projection,
            )
            return DocumentList(
                items=[store_doc_to_api_doc(doc) for doc in docs],
                offset=offset,
                total=total,
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
