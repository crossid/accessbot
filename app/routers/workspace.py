import logging
from typing import Annotated, Optional

import jsonpatch
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, HttpUrl, ValidationError
from starlette import status

from ..auth import (
    CurrentUser,
    get_current_active_user,
    get_current_workspace,
    setup_workspace_vstore,
)
from ..models import JsonPatchDocument, PatchOperation, Workspace
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
    logo_url: Optional[HttpUrl] = None
    display_name: str


@router.post(
    "",
    response_model=Workspace,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: CreateWorkspaceBody,
    background_tasks: BackgroundTasks,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    workspace_store: WorkspaceStore = Depends(get_service(WorkspaceStore)),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            ws = Workspace(
                external_id=body.external_id,
                display_name=body.display_name,
                logo_url=body.logo_url.unicode_string() if body.logo_url else None,
                created_by=current_user.id,
                config={},
            )
            # note: this is required for the hooks to work
            current_user.workspace_id = ws.id
            pws = workspace_store.insert(
                workspace=ws,
                current_user=current_user,
                background_tasks=background_tasks,
                tx_context=tx_context,
            )
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
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    tx_context: TransactionContext,
    workspace_store: WorkspaceStore,
    msg_store: ChatMessageStore,
    conversation_store: ConversationStore,
    background_tasks: BackgroundTasks,
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

    workspace_store.delete(
        workspace=workspace,
        current_user=current_user,
        background_tasks=background_tasks,
        tx_context=tx_context,
    )


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    workspace_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    background_tasks: BackgroundTasks,
    workspace_store: Annotated[WorkspaceStore, Depends(get_service(WorkspaceStore))],
    msg_store: Annotated[ChatMessageStore, Depends(factory_message_store)],
    conversation_store: Annotated[
        ConversationStore, Depends(factory_conversation_store)
    ],
    ovstore=Depends(setup_workspace_vstore),
):
    if current_user.id != workspace.created_by or workspace_id != workspace.id:
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
            current_user=current_user,
            tx_context=tx_context,
            workspace_store=workspace_store,
            conversation_store=conversation_store,
            background_tasks=background_tasks,
            msg_store=msg_store,
            ovstore=ovstore,
        )


class WorkspacePatchOperation(PatchOperation):
    mutable_fields = ["display_name", "logo_url", "config"]


WorkspaceJsonPatchDocument = JsonPatchDocument[WorkspacePatchOperation]


@router.patch(
    "/{workspace_id}",
    response_model=Workspace,
    response_model_exclude_none=True,
)
async def update_org(
    body: WorkspaceJsonPatchDocument,
    workspace_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    workspace_store: Annotated[WorkspaceStore, Depends(get_service(WorkspaceStore))],
):
    try:
        with SQLAlchemyTransactionContext().manage() as tx_context:
            ws_dict = workspace.model_dump()
            body_dict = body.model_dump()
            patch = jsonpatch.JsonPatch(body_dict["patch"])
            ws_updated_dict = patch.apply(ws_dict)
            ws_updated = Workspace(**ws_updated_dict)
            workspace = workspace_store.update(
                workspace=ws_updated, tx_context=tx_context
            )
            return workspace
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
