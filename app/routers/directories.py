import logging
from typing import Annotated, Any, List, Optional

import jsonpatch
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError
from pydantic_core import ErrorDetails

from app.authz import Permissions, is_admin_or_has_scopes
from app.data_fetching.factory import DataFetcherFactory, background_data_fetch
from app.models_stores_sql import PartialDirectory

from ..auth import (
    get_current_active_user,
    get_current_workspace,
    setup_workspace_vstore,
)
from ..models import (
    CurrentUser,
    Directory,
    JsonPatchDocument,
    PaginatedListBase,
    PatchOperation,
    Workspace,
)
from ..models_stores import DirectoryStore
from ..services import get_service, pagination_params
from ..sql import SQLAlchemyTransactionContext

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/directories",
    tags=["directories"],
)


class CreateDirectoryBody(BaseModel):
    name: str
    provisioning_config: Optional[dict] = None
    read_config: Optional[dict] = None
    data_owner_config: Optional[dict] = None


@router.post(
    "",
    response_model=Directory,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: CreateDirectoryBody,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    directory_store: DirectoryStore = Depends(get_service(DirectoryStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_DIRECTORIES.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            dir = Directory(
                workspace_id=workspace.id,
                name=body.name,
                provisioning_config=body.provisioning_config,
                read_config=body.read_config,
                data_owner_config=body.data_owner_config,
                created_by=current_user.email,
            )
            pdir = directory_store.insert(
                dir=dir,
                tx_context=tx_context,
            )
            return pdir
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.json())
        except HTTPException as e:
            # we know that 409 is always a unique constraint violation on name field
            if e.status_code == 409:
                error = ErrorDetails(
                    type="uniqueness",
                    loc=("body", "name"),
                    msg=f"name '{body.name}' already exists",
                )
                raise HTTPException(status_code=409, detail=[error])
            else:
                raise e
        except Exception as e:
            status_code = (
                e.status_code
                if hasattr(e, "status_code")
                else status.HTTP_400_BAD_REQUEST
            )
            detail = e.detail if hasattr(e, "detail") else e.message
            raise HTTPException(status_code=status_code, detail=detail)


@router.get(
    "/{directory_id}", response_model=Directory, response_model_exclude_none=True
)
def get(
    directory_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    directory_store: DirectoryStore = Depends(get_service(DirectoryStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.READ_DIRECTORIES.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        dir = directory_store.get_by_id(
            directory_id=directory_id, workspace_id=workspace.id, tx_context=tx_context
        )
        if not dir:
            raise HTTPException(status_code=404, detail="Directory not found")
        return dir


@router.delete("/{directory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    directory_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    directory_store: Annotated[DirectoryStore, Depends(get_service(DirectoryStore))],
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.DELETE_DIRECTORIES.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        directory_store.delete(
            directory_id=directory_id,
            workspace_id=workspace.id,
            tx_context=tx_context,
        )


class DirectoryPatchOperation(PatchOperation):
    mutable_fields = ["provisioning_config", "data_owner_config", "read_config"]


DirectoryJsonPatchDocument = JsonPatchDocument[DirectoryPatchOperation]


@router.patch(
    "/{directory_id}",
    response_model=Directory,
    response_model_exclude_none=True,
)
async def update_directory(
    body: DirectoryJsonPatchDocument,
    directory_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    directory_store: Annotated[DirectoryStore, Depends(get_service(DirectoryStore))],
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_DIRECTORIES.value])),
):
    try:
        with SQLAlchemyTransactionContext().manage() as tx_context:
            dir = directory_store.get_by_id(
                directory_id=directory_id,
                workspace_id=workspace.id,
                tx_context=tx_context,
            )
            if not dir:
                raise HTTPException(status_code=404, detail="Directory not found")

            dir_dict = dir.model_dump()
            body_dict = body.model_dump()
            patch = jsonpatch.JsonPatch(body_dict["patch"])
            dir_updated_dict = patch.apply(dir_dict)
            dir_updated = Directory(**dir_updated_dict)
            directory = directory_store.update(
                directory=dir_updated, tx_context=tx_context
            )
            return directory
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


class DirectoryList(PaginatedListBase):
    items: List[PartialDirectory]


@router.get("", response_model=DirectoryList, response_model_exclude_none=True)
async def list(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    directory_store: Annotated[DirectoryStore, Depends(get_service(DirectoryStore))],
    list_params: dict = Depends(pagination_params),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.READ_DIRECTORIES.value])),
):
    limit = list_params.get("limit", 10)
    offset = list_params.get("offset", 0)
    projection = list_params.get("projection", None)
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            items, count = directory_store.list(
                workspace_id=workspace.id,
                tx_context=tx_context,
                limit=limit,
                offset=offset,
                projection=projection,
            )
            return DirectoryList(
                items=items,
                offset=offset,
                total=count,
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())


@router.post(
    "/{dir_id}/.import", response_model=dict, status_code=status.HTTP_202_ACCEPTED
)
async def import_content(
    body: dict[str, Any],
    dir_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    directory_store: Annotated[DirectoryStore, Depends(get_service(DirectoryStore))],
    background_tasks: BackgroundTasks,
    ovstore=Depends(setup_workspace_vstore),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_CONTENT.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        dir = directory_store.get_by_id(
            directory_id=dir_id, workspace_id=workspace.id, tx_context=tx_context
        )

        if not dir:
            raise HTTPException(status_code=404, detail="Directory not found")

    data_fetcher = DataFetcherFactory(dir=dir)
    background_tasks.add_task(background_data_fetch, data_fetcher, ovstore, dir, **body)
    return {"message": "data import happening in background"}
