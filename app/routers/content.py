import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import setup_workspace_vstore
from ..id import generate
from ..settings import settings
from ..vector_store import delete_ids, get_protocol

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/content",
    tags=["content"],
)


class Doc(BaseModel):
    id: Optional[str]
    metadata: Optional[dict[str, Any]]
    content: str


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
        metadatas.append(doc.metadata if doc.metadata is not None else {})
        ids.append(doc.id if doc.id is not None else generate())
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
