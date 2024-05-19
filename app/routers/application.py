import logging
from typing import Annotated, Optional

import jsonpatch
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

from ..auth import get_current_workspace
from ..models import Application, JsonPatchDocument, PatchOperation, Workspace
from ..models_stores import ApplicationStore
from ..services import get_service
from ..sql import SQLAlchemyTransactionContext

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/applications",
    tags=["applications"],
)


class CreateApplicationBody(BaseModel):
    display_name: str
    aliases: list[str]
    extra_instructions: Optional[str] = None


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
                display_name=body.display_name,
                aliases=body.aliases,
                extra_instructions=body.extra_instructions,
            )
            papp = application_store.insert(
                app=app,
                tx_context=tx_context,
            )
            return papp
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
        except Exception as e:
            if hasattr(e, "status_code") and e.status_code is not None:
                detail = e.detail if hasattr(e, "detail") else e.message
                raise HTTPException(status_code=e.status_code, detail=detail)

            raise e


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
    mutable_fields = ["aliases", "extra_instructions"]


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
