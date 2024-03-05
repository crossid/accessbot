import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from starlette import status

from ..auth import (
    CurrentUser,
    get_current_active_user,
    setup_org_vstore,
)
from ..models import Org
from ..models_facade import ChatMessageFacade, ConversationStore, OrgFacade
from ..services import (
    factory_conversation_db_facade,
    factory_message_db_facade,
    get_service,
)
from ..sql import SQLAlchemyTransactionContext
from ..tx import TransactionContext
from ..vector_store import delete_store

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/orgs",
    tags=["orgs"],
)


class CreateOrgRequest(BaseModel):
    external_id: Optional[str] = None
    display_name: str
    config: dict[str, Any] = Field(description="Organization configuration")


@router.post(
    "",
    response_model=Org,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: CreateOrgRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_facade: OrgFacade = Depends(get_service(OrgFacade)),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            org = Org(**body.model_dump(exclude_none=True), creator_id=current_user.id)
            porg = org_facade.insert(org, tx_context=tx_context)
            return porg
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


@router.get("/{org_id}", response_model=Org, response_model_exclude_none=True)
def get(
    org_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_facade: OrgFacade = Depends(get_service(OrgFacade)),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        org = org_facade.get_by_id(org_id, tx_context=tx_context)
        # TODO check if user is a member of the org, oterhwise return 404
        if not org:
            raise HTTPException(status_code=404, detail="Org not found")
        return org


def wipe_org(
    org: Org,
    tx_context: TransactionContext,
    org_facade: OrgFacade,
    msg_facade: ChatMessageFacade,
    req_facade: ConversationStore,
    ovstore,
):
    delete_store(ovstore=ovstore)
    msg_facade.delete_for_org(org_id=org.id, tx_context=tx_context)
    req_facade.delete_for_org(org_id=org.id, tx_context=tx_context)
    org_facade.delete(org=org, tx_context=tx_context)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    org_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_facade: Annotated[OrgFacade, Depends(get_service(OrgFacade))],
    msg_facade: Annotated[ChatMessageFacade, Depends(factory_message_db_facade)],
    req_facade: Annotated[ConversationStore, Depends(factory_conversation_db_facade)],
    ovstore=Depends(setup_org_vstore),
):
    # TODO: authorization, replace this check with creator_id?

    if org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to delete this org",
        )

    with SQLAlchemyTransactionContext().manage() as tx_context:
        current_org = org_facade.get_by_id(org_id=org_id, tx_context=tx_context)
        if current_org is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="org not found",
            )

        wipe_org(
            org=current_org,
            tx_context=tx_context,
            org_facade=org_facade,
            req_facade=req_facade,
            msg_facade=msg_facade,
            ovstore=ovstore,
        )
