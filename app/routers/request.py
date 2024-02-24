import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
from starlette import status

from app.auth import get_current_active_user
from app.models import AccessRequest, CurrentUser
from app.models_facade import OrgFacade
from app.services import factory_org_db_facade, factory_request_db_facade
from app.sql import SQLAlchemyTransactionContext

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/requests",
    tags=["requests"],
)


class AccessRequestBody(BaseModel):
    pass


@router.post(
    "",
    response_model=AccessRequest,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: AccessRequestBody,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    request_facade: OrgFacade = Depends(factory_request_db_facade),
    org_facade: OrgFacade = Depends(factory_org_db_facade),
):
    org_id = None
    if current_user.org_id is not None:
        org = org_facade.get_by_id(org_id=current_user.org_id)
        org_id = org.id
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            ar = AccessRequest(
                org_id=org_id, owner_id=current_user.id, context={}, messages=[]
            )
            par = request_facade.insert(ar, tx_context=tx_context)
            return par
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


class ConversationBody(BaseModel):
    content: str


@router.post(
    "/{request_id}/conversation",
    response_model=AccessRequest,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
def conversation(
    request_id: str,
    body: ConversationBody,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    request_facade: OrgFacade = Depends(factory_request_db_facade),
    org_facade: OrgFacade = Depends(factory_org_db_facade),
):
    ar = request_facade.get_by_id(request_id)
    if ar is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found"
        )

    return StreamingResponse(
        stream_conversation(
            current_user=current_user,
            request=ar,
            input=body.input,
        ),
        media_type="text/event-stream",
    )
