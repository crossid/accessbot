import asyncio
import logging
from typing import Annotated, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import (
    get_current_active_user,
    get_current_workspace,
)
from app.authz import Permissions, is_admin_or_has_scopes
from app.llm.access_prediction import (
    dict_to_md,
    format_response,
    predict_access_to_user,
)
from app.models import (
    CurrentUser,
    Workspace,
)
from app.models_stores import ApplicationStore
from app.services import get_service
from app.sql import SQLAlchemyTransactionContext

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/predictions",
    tags=["predictions"],
)


class PredictAccessForUserBody(BaseModel):
    user: dict[str, Any]
    application_ids: List[str] = Field(default=[])
    top_k: Optional[int] = Field(description="", default=10)
    min_relevance: Optional[float] = Field(default=0.7)
    output_instructions: Optional[str] = Field(default=None)


@router.post(
    "/access_for_user",
)
async def predict_access_for_user(
    body: PredictAccessForUserBody,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    application_store: ApplicationStore = Depends(get_service(ApplicationStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.ADMIN.value])),
):
    applications = []
    user_md = dict_to_md(body.user)
    with SQLAlchemyTransactionContext().manage() as tx_context:
        # Find all applications from application_ids
        for app_id in body.application_ids:
            app = application_store.get_by_id(
                app_id=app_id, workspace_id=workspace.id, tx_context=tx_context
            )
            if app:
                applications.append(app)

        # Verify at least 1 application exists
        if not applications:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No valid applications found for the given application_ids",
            )

    # Run predict_access_to_user for each application simultaneously
    tasks = [
        predict_access_to_user(
            user_md=user_md,
            ws=workspace,
            app=app,
            top_k=body.top_k,
            min_relevance=body.min_relevance,
        )
        for app in applications
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results and handle exceptions
    error_results = []
    processed_results = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Error in predict_access_to_user: {str(result)}")
            error_results.append(f"Error occurred: {str(result)}")
        else:
            processed_results.append(result)

    if not processed_results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"all applications returned errors. {str(error_results)}",
        )

    # Combine results and format output, if necessary
    if not body.output_instructions:
        return {"prediction": processed_results}

    # Combine results and format output
    formatted_output = await format_response(
        predictions=processed_results, output_instructions=body.output_instructions
    )

    return {"prediction": formatted_output}
