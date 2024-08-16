import logging
from typing import Annotated, List, Optional

import jsonpatch
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

from app.authz import Permissions, is_admin_or_has_scopes

from ..auth import get_current_workspace
from ..models import (
    Application,
    JsonPatchDocument,
    PaginatedListBase,
    PartialApplication,
    PatchOperation,
    Workspace,
)
from ..models_stores import ApplicationStore
from ..services import factory_app_store, get_service, pagination_params
from ..sql import SQLAlchemyTransactionContext

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/applications",
    tags=["applications"],
)


class CreateApplicationBody(BaseModel):
    name: str
    aliases: list[str]
    extra_instructions: Optional[str] = None
    provision_schema: Optional[dict] = None


@router.post(
    "",
    response_model=Application,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: CreateApplicationBody,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    application_store: ApplicationStore = Depends(get_service(ApplicationStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_APPLICATIONS.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            app = Application(
                workspace_id=workspace.id,
                name=body.name,
                aliases=body.aliases,
                provision_schema=body.provision_schema,
                extra_instructions=body.extra_instructions,
            )
            papp = application_store.insert(
                app=app,
                tx_context=tx_context,
            )
            return papp
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.json()
            )
        except HTTPException as e:
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
    "/{application_id}", response_model=Application, response_model_exclude_none=True
)
def get(
    application_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    application_store: ApplicationStore = Depends(get_service(ApplicationStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.READ_APPLICATIONS.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        app = application_store.get_by_id(
            app_id=application_id, workspace_id=workspace.id, tx_context=tx_context
        )
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        return app


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    application_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    application_store: Annotated[
        ApplicationStore, Depends(get_service(ApplicationStore))
    ],
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.DELETE_APPLICATIONS.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        application_store.delete(
            app_id=application_id,
            workspace_id=workspace.id,
            tx_context=tx_context,
        )


class ApplicationPatchOperation(PatchOperation):
    mutable_fields = ["aliases", "extra_instructions", "provision_schema"]


ApplicationJsonPatchDocument = JsonPatchDocument[ApplicationPatchOperation]


@router.patch(
    "/{application_id}",
    response_model=Application,
    response_model_exclude_none=True,
)
async def update_application(
    body: ApplicationJsonPatchDocument,
    application_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    application_store: Annotated[
        ApplicationStore, Depends(get_service(ApplicationStore))
    ],
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_APPLICATIONS.value])),
):
    try:
        with SQLAlchemyTransactionContext().manage() as tx_context:
            app = application_store.get_by_id(
                app_id=application_id, workspace_id=workspace.id, tx_context=tx_context
            )
            if not app:
                raise HTTPException(status_code=404, detail="Application not found")

            app_dict = app.model_dump()
            body_dict = body.model_dump()
            patch = jsonpatch.JsonPatch(body_dict["patch"])
            app_updated_dict = patch.apply(app_dict)
            app_updated = Application(**app_updated_dict)
            application = application_store.update(
                application=app_updated, tx_context=tx_context
            )
            return application
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


class ApplicationList(PaginatedListBase):
    items: List[PartialApplication]


@router.get("", response_model=ApplicationList, response_model_exclude_none=True)
async def list(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    list_params: dict = Depends(pagination_params),
    app_store: ApplicationStore = Depends(factory_app_store),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.READ_APPLICATIONS.value])),
):
    limit = list_params.get("limit", 10)
    offset = list_params.get("offset", 0)
    projection = list_params.get("projection", None)
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            items, count = app_store.list(
                workspace_id=workspace.id,
                tx_context=tx_context,
                limit=limit,
                offset=offset,
                projection=projection,
            )
            return ApplicationList(
                items=items,
                offset=offset,
                total=count,
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
