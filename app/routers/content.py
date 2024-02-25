import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_active_user
from app.embeddings import create_embedding
from app.models import CurrentUser
from app.models_facade import OrgFacade
from app.services import factory_org_db_facade
from app.settings import settings
from app.sql import SQLAlchemyTransactionContext
from app.vector_store import create_org_vstore

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/content",
    tags=["content"],
)


class AddContentBody(BaseModel):
    texts: List[str]


class AddContentResponse(BaseModel):
    ok: bool


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


@router.post("", response_model=AddContentResponse)
async def add(
    body: AddContentBody,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_facade: OrgFacade = Depends(factory_org_db_facade),
):
    ovstore = setup_org_vstore(current_user=current_user, org_facade=org_facade)
    ovstore.add_texts(body.texts)
    return AddContentResponse(ok=True)
