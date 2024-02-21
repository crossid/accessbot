import logging
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
from starlette import status

from app.auth import (
    CurrentUser,
    get_current_active_user,
)
from app.models import Org
from app.models_facade import OrgFacade
from app.services import factory_org_db_facade

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/orgs",
    tags=["orgs"],
)


class CreateOrgRequest(BaseModel):
    external_id: Optional[str] = None
    display_name: str
    config: dict[str, Any] = Field(description="Organization configuration")


@router.post(
    "",
    response_model=Org,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: CreateOrgRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_facade: OrgFacade = Depends(factory_org_db_facade),
):
    try:
        org = Org(**body.model_dump(exclude_none=True), creator_id=current_user.id)
        porg = org_facade.insert(org)
        return porg
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


@router.get("/{org_id}", response_model=Org, response_model_exclude_none=True)
def get(
    org_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    org_facade: OrgFacade = Depends(factory_org_db_facade),
):
    org = org_facade.get_by_id(org_id)
    # TODO check if user is a member of the org, oterhwise return 404
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")
    return org
