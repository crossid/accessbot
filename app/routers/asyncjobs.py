import enum
from typing import Annotated, Any, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app import celery_app
from app.auth import get_current_workspace
from app.models import Workspace

router = APIRouter(prefix="/async-jobs", tags=["async jobs"])


class AsyncJobStatus(enum.Enum):
    pending = "pending"
    failure = "failure"
    success = "success"


class AsyncJob(BaseModel):
    id: str
    status: AsyncJobStatus
    task_name: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    args: Optional[list] = None
    kwargs: Optional[dict] = None
    # created_at: datetime
    # updated_at: datetime


@router.get(
    "/{job_id}",
    response_model=AsyncJob,
    response_model_exclude_none=True,
)
async def get_job(
    job_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    # _=Depends(is_admin_or_has_scopes(scopes=[Permissions.READ_SECRETS.value])),
):
    try:
        result = AsyncResult(job_id, app=celery_app.celery_app)

        job = AsyncJob(
            id=job_id,
            status=AsyncJobStatus.pending
            if result.state == "PENDING"
            else AsyncJobStatus.failure
            if result.state == "FAILURE"
            else AsyncJobStatus.success
            if result.state == "SUCCESS"
            else None,
            # task_name=result.task_name if hasattr(result, "task_name") else None,
            result=result.result if result.state == "SUCCESS" else None,
            error=str(result.info) if result.state == "FAILURE" else None,
            # args=result.args if hasattr(result, "args") else None,
            # kwargs=result.kwargs if hasattr(result, "kwargs") else None,
            # created_at=result.date_created
            # if hasattr(result, "date_created")
            # else datetime.utcnow(),
            # updated_at=datetime.utcnow(),
        )

        return job
    except Exception as e:
        # detail = e.detail if hasattr(e, "detail") else e.message
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
