import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
from starlette import status
from zmq import Enum

from ..auth import get_current_active_user, get_current_workspace
from ..llm.conversation import (
    add_messages,
    create_agent_for_access_request_conversation,
    sse_client_transformer,
)
from ..llm.prompts import CONVERSATION_ID_KEY, MEMORY_KEY, USERNAME_KEY, WS_ID_KEY
from ..llm.sql_chat_message_history import LangchainChatMessageHistory
from ..llm.streaming import streaming
from ..models import Conversation, CurrentUser, PaginatedListBase, Workspace
from ..models_stores import ChatMessageStore, ConversationStore
from ..services import (
    factory_conversation_store,
    factory_message_store,
    pagination_params,
)
from ..sql import SQLAlchemyTransactionContext

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)


class CreateConversationBody(BaseModel):
    external_id: Optional[str] = None


@router.post(
    "",
    response_model=Conversation,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: CreateConversationBody,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    conversation_store: ConversationStore = Depends(factory_conversation_store),
):
    workspace_id = workspace.id
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            ar = Conversation(
                workspace_id=workspace_id,
                created_by=current_user.id,
                context={},
                external_id=body.external_id,
                messages=None,
            )
            par = conversation_store.insert(ar, tx_context=tx_context)
            return par
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


class IDType(str, Enum):
    internal = "internal"
    external = "external"


@router.get(
    "/{conversation_id}", response_model=Conversation, response_model_exclude_none=True
)
def get(
    conversation_id,
    # current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    id_type: IDType = IDType.internal,
    conversation_store: ConversationStore = Depends(factory_conversation_store),
    links: List[str] = Query(None),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            conv: Conversation
            if id_type == IDType.internal:
                conv = conversation_store.get_by_id(
                    workspace_id=workspace.id,
                    conversation_id=conversation_id,
                    links=links,
                    tx_context=tx_context,
                )
            else:
                conv = conversation_store.get_by_external_id(
                    workspace_id=workspace.id,
                    external_id=conversation_id,
                    links=links,
                    tx_context=tx_context,
                )
            if conv is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="conversation not found",
                )
            return conv
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


class ConversationList(PaginatedListBase):
    items: List[Conversation]


@router.get("", response_model=ConversationList, response_model_exclude_none=True)
def list(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    list_params: dict = Depends(pagination_params),
    conversation_store: ConversationStore = Depends(factory_conversation_store),
    links: List[str] = Query(None),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            items, count = conversation_store.list(
                workspace_id=workspace.id,
                tx_context=tx_context,
                links=links,
                limit=list_params["limit"],
                offset=list_params["offset"],
                filters={"created_by": current_user.id},
            )
            return ConversationList(items=items, offset=0, total=count)
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


class ConversationBody(BaseModel):
    input: str


@router.post(
    "/{conversation_id}/stream",
    response_model=Conversation,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
)
async def conversation(
    conversation_id: str,
    body: ConversationBody,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    workspace: Annotated[Workspace | None, Depends(get_current_workspace)],
    conversation_store: ConversationStore = Depends(factory_conversation_store),
    message_store: ChatMessageStore = Depends(factory_message_store),
):
    workspace_id = workspace.id

    with SQLAlchemyTransactionContext().manage() as tx_context:

        def _add_messages(ai_content: str):
            # Open a new TX because the main tx gets closed after the response is sent which is before the cb is invoked
            with SQLAlchemyTransactionContext().manage() as tx_context:
                chat_history = LangchainChatMessageHistory(
                    conversation_id=conversation_id,
                    workspace_id=workspace_id,
                    tx_context=tx_context,
                    store=message_store,
                )
                add_messages(
                    chat_history=chat_history,
                    user_input=body.input,
                    ai_content=ai_content,
                )

        chat_history = LangchainChatMessageHistory(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            tx_context=tx_context,
            store=message_store,
        )
        ar = conversation_store.get_by_id(
            conversation_id=conversation_id,
            workspace_id=workspace_id,
            tx_context=tx_context,
        )
        if ar is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found"
            )

        agent_executor = create_agent_for_access_request_conversation(ar)

        return StreamingResponse(
            streaming(
                agent_executor,
                {
                    "input": body.input,
                    MEMORY_KEY: chat_history.messages,
                    USERNAME_KEY: current_user.id,
                    WS_ID_KEY: ar.workspace_id,
                    CONVERSATION_ID_KEY: ar.id,
                },
                event_transformer=sse_client_transformer,
                callback=_add_messages,
            ),
            media_type="text/event-stream",
        )
