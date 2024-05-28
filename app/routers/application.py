import logging
from typing import Annotated, List, Optional

import jsonpatch
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

from ..auth import get_current_workspace
from ..models import (
    Application,
    JsonPatchDocument,
    PaginatedListBase,
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
    unique_name: str
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
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            app = Application(
                workspace_id=workspace.id,
                unique_name=body.unique_name,
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
            raise HTTPException(status_code=422, detail=e.json())
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
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        app = application_store.get_by_id(
            app_id=application_id, workspace_id=workspace.id, tx_context=tx_context
        )
        if app is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

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


class PApplication(BaseModel):
    id: str | None
    workspace_id: str | None
    unique_name: str | None
    aliases: list[str] | None
    extra_instructions: str | None
    provision_schema: dict | None

    @staticmethod
    def from_app(app: Application):
        return PApplication(
            id=app.id or None,
            workspace_id=app.workspace_id or None,
            unique_name=app.unique_name or None,
            aliases=app.aliases or None,
            extra_instructions=app.extra_instructions or None,
            provision_schema=app.provision_schema or None,
        )


class ApplicationList(PaginatedListBase):
    items: List[PApplication]


@router.get("", response_model=ApplicationList, response_model_exclude_none=True)
async def list(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    list_params: dict = Depends(pagination_params),
    app_store: ApplicationStore = Depends(factory_app_store),
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
                items=[PApplication.from_app(app) for app in items],
                offset=offset,
                total=count,
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
