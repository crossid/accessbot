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
from ..models_stores import ChatMessageStore, ConversationStore, OrgStore
from ..services import (
    factory_conversation_store,
    factory_message_store,
    factory_vault,
    get_service,
)
from ..sql import SQLAlchemyTransactionContext
from ..tx import TransactionContext
from ..vault import VaultAPI
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
    org_store: OrgStore = Depends(get_service(OrgStore)),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            org = Org(**body.model_dump(exclude_none=True), creator_id=current_user.id)
            porg = org_store.insert(org, tx_context=tx_context)
            return porg
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


@router.get("/{org_id}", response_model=Org, response_model_exclude_none=True)
def get(
    org_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_store: OrgStore = Depends(get_service(OrgStore)),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        org = org_store.get_by_id(org_id, tx_context=tx_context)
        # TODO check if user is a member of the org, oterhwise return 404
        if not org:
            raise HTTPException(status_code=404, detail="Org not found")
        return org


def wipe_org(
    org: Org,
    tx_context: TransactionContext,
    org_store: OrgStore,
    msg_store: ChatMessageStore,
    conversation_store: ConversationStore,
    ovstore,
):
    delete_store(ovstore=ovstore)
    msg_store.delete_for_org(org_id=org.id, tx_context=tx_context)
    conversation_store.delete_for_org(org_id=org.id, tx_context=tx_context)

    vault: VaultAPI = factory_vault()
    org_secrets = vault.list_secrets(org_id=org.id)
    for name in org_secrets:
        vault.delete_secret(org_id=org.id, path=name)

    org_store.delete(org=org, tx_context=tx_context)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    org_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_store: Annotated[OrgStore, Depends(get_service(OrgStore))],
    msg_store: Annotated[ChatMessageStore, Depends(factory_message_store)],
    conversation_store: Annotated[
        ConversationStore, Depends(factory_conversation_store)
    ],
    ovstore=Depends(setup_org_vstore),
):
    # TODO: authorization, replace this check with creator_id?

    if org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to delete this org",
        )

    with SQLAlchemyTransactionContext().manage() as tx_context:
        current_org = org_store.get_by_id(org_id=org_id, tx_context=tx_context)
        if current_org is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="org not found",
            )

        wipe_org(
            org=current_org,
            tx_context=tx_context,
            org_store=org_store,
            req_store=conversation_store,
            msg_store=msg_store,
            ovstore=ovstore,
        )
