import logging
from typing import Annotated, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_active_user
from app.embeddings import create_embedding
from app.id import generate
from app.models import CurrentUser
from app.models_facade import OrgFacade
from app.services import factory_org_db_facade
from app.settings import settings
from app.sql import SQLAlchemyTransactionContext
from app.vector_store import create_org_vstore, delete_ids, get_protocol

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


def setup_org_vstore(current_user: CurrentUser, org_facade: OrgFacade):
    if current_user.org_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="current user is not a member of an org",
        )

    with SQLAlchemyTransactionContext().manage() as tx_context:
        org = org_facade.get_by_id(org_id=current_user.org_id, tx_context=tx_context)
        if org is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="org not found"
            )
        ovstore = create_org_vstore(org.id, create_embedding(settings.VSTORE_EMBEDDING))
        return ovstore


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
async def add(
    body: AddContentBody,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_facade: OrgFacade = Depends(factory_org_db_facade),
):
    ovstore = setup_org_vstore(current_user=current_user, org_facade=org_facade)
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
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_facade: OrgFacade = Depends(factory_org_db_facade),
):
    ovstore = setup_org_vstore(current_user=current_user, org_facade=org_facade)
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
