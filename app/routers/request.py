import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
from starlette import status

from ..auth import get_current_active_user, get_optional_current_org
from ..llm.conversation import (
    add_messages,
    create_agent_for_access_request_conversation,
    sse_client_transformer,
)
from ..llm.prompts import MEMORY_KEY, ORGID_KEY, REQUEST_ID_KEY, USERNAME_KEY
from ..llm.sql_chat_message_history import LangchainChatMessageHistory
from ..llm.streaming import streaming
from ..models import AccessRequest, CurrentUser, Org
from ..models_facade import ChatMessageFacade, OrgFacade
from ..services import (
    factory_message_db_facade,
    factory_org_db_facade,
    factory_request_db_facade,
)
from ..sql import SQLAlchemyTransactionContext

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
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            if current_user.org_id is not None:
                org = org_facade.get_by_id(
                    org_id=current_user.org_id, tx_context=tx_context
                )
                org_id = org.id

            ar = AccessRequest(
                org_id=org_id, requestee_id=current_user.id, context={}, messages=None
            )
            par = request_facade.insert(ar, tx_context=tx_context)
            return par
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


@router.get(
    "/{request_id}", response_model=AccessRequest, response_model_exclude_none=True
)
def get(
    request_id,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    request_facade: OrgFacade = Depends(factory_request_db_facade),
    links: List[str] = Query(None),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        if current_user.org_id is None:
            raise HTTPException(status_code=403, detail="current user has no org")

        try:
            r = request_facade.get_by_id(
                org_id=current_user.org_id,
                request_id=request_id,
                links=links,
                tx_context=tx_context,
            )
            if r is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="request not found"
                )
            return r
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


class ConversationBody(BaseModel):
    input: str


@router.post(
    "/{request_id}/conversation/stream",
    response_model=AccessRequest,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
async def conversation(
    request_id: str,
    body: ConversationBody,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    optional_org: Annotated[Org | None, Depends(get_optional_current_org)],
    request_facade: OrgFacade = Depends(factory_request_db_facade),
    message_facade: ChatMessageFacade = Depends(factory_message_db_facade),
):
    org_id = optional_org.id if optional_org is not None else None

    with SQLAlchemyTransactionContext().manage() as tx_context:

        def _add_messages(ai_content: str):
            # Open a new TX because the main tx gets closed after the response is sent which is before the cb is invoked.
            with SQLAlchemyTransactionContext().manage() as tx_context:
                chat_history = LangchainChatMessageHistory(
                    conversation_id=request_id,
                    org_id=org_id,
                    tx_context=tx_context,
                    facade=message_facade,
                )
                add_messages(
                    chat_history=chat_history,
                    user_input=body.input,
                    ai_content=ai_content,
                )

        chat_history = LangchainChatMessageHistory(
            conversation_id=request_id,
            org_id=org_id,
            tx_context=tx_context,
            facade=message_facade,
        )
        ar = request_facade.get_by_id(
            request_id=request_id, org_id=org_id, tx_context=tx_context
        )
        if ar is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="request not found"
            )

        agent_executor = create_agent_for_access_request_conversation(ar)

        return StreamingResponse(
            streaming(
                agent_executor,
                {
                    "input": body.input,
                    MEMORY_KEY: chat_history.messages,
                    USERNAME_KEY: current_user.id,
                    ORGID_KEY: ar.org_id,
                    REQUEST_ID_KEY: ar.id,
                },
                event_transformer=sse_client_transformer,
                callback=_add_messages,
            ),
            media_type="text/event-stream",
        )
