import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from starlette import status

from ..auth import (
    CurrentUser,
    get_current_active_user,
    get_current_workspace,
    setup_workspace_vstore,
)
from ..models import Workspace
from ..models_stores import ChatMessageStore, ConversationStore, WorkspaceStore
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
    prefix="/workspaces",
    tags=["workspaces"],
)


class CreateWorkspaceBody(BaseModel):
    external_id: Optional[str] = None
    display_name: str
    config: dict[str, Any] = Field(description="Workspace configuration")


@router.post(
    "",
    response_model=Workspace,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: CreateWorkspaceBody,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    workspace_store: WorkspaceStore = Depends(get_service(WorkspaceStore)),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            ws = Workspace(
                **body.model_dump(exclude_none=True), creator_id=current_user.id
            )
            pws = workspace_store.insert(ws, tx_context=tx_context)
            return pws
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code is not None:
                detail = e.detail if hasattr(e, "detail") else e.message
                raise HTTPException(status_code=e.status_code, detail=detail)

            raise e


@router.get(
    "/{workspace_id}", response_model=Workspace, response_model_exclude_none=True
)
def get(
    workspace_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    workspace_store: WorkspaceStore = Depends(get_service(WorkspaceStore)),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        ws = workspace_store.get_by_id(workspace_id, tx_context=tx_context)
        # TODO check if user is a member of the workspace, oterhwise return 404
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return ws


def wipe_workspace(
    workspace: Workspace,
    tx_context: TransactionContext,
    workspace_store: WorkspaceStore,
    msg_store: ChatMessageStore,
    conversation_store: ConversationStore,
    ovstore,
):
    delete_store(ovstore=ovstore)
    msg_store.delete_for_workspace(workspace_id=workspace.id, tx_context=tx_context)
    conversation_store.delete_for_workspace(
        workspace_id=workspace.id, tx_context=tx_context
    )

    vault: VaultAPI = factory_vault()
    ws_secrets = vault.list_secrets(workspace_id=workspace.id)
    for name in ws_secrets:
        vault.delete_secret(workspace_id=workspace.id, path=name)

    workspace_store.delete(workspace=workspace, tx_context=tx_context)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    workspace_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    workspace_store: Annotated[WorkspaceStore, Depends(get_service(WorkspaceStore))],
    msg_store: Annotated[ChatMessageStore, Depends(factory_message_store)],
    conversation_store: Annotated[
        ConversationStore, Depends(factory_conversation_store)
    ],
    ovstore=Depends(setup_workspace_vstore),
):
    if current_user.id != workspace.creator_id or workspace_id != workspace.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to delete this workspace",
        )

    with SQLAlchemyTransactionContext().manage() as tx_context:
        current_ws = workspace_store.get_by_id(
            workspace_id=workspace_id, tx_context=tx_context
        )
        if current_ws is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="workspace not found",
            )

        wipe_workspace(
            workspace=current_ws,
            tx_context=tx_context,
            workspace_store=workspace_store,
            conversation_store=conversation_store,
            msg_store=msg_store,
            ovstore=ovstore,
        )
