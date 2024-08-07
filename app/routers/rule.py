import logging
from typing import Annotated, List, Optional

import jsonpatch
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.authz import Permissions, is_admin_or_has_scopes

from ..auth import get_current_active_user, get_current_workspace
from ..models import (
    RULE_MUTABLE_FIELDS,
    CurrentUser,
    JsonPatchDocument,
    PaginatedListBase,
    PartialRule,
    PatchOperation,
    Rule,
    RuleTypes,
    ThenTypes,
    Workspace,
)
from ..models_stores import RuleStore
from ..services import get_service, pagination_params
from ..sql import SQLAlchemyTransactionContext

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/rules",
    tags=["rules"],
)


class CreateRuleBody(BaseModel):
    when: str
    then: ThenTypes
    type: RuleTypes
    active: Optional[bool] = Field(default=False)
    directory_ids: Optional[List[str]] = Field(default=None)
    application_ids: Optional[List[str]] = Field(default=None)


@router.post(
    "",
    response_model=Rule,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
)
def create(
    body: CreateRuleBody,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
    rule_store: RuleStore = Depends(get_service(RuleStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_RULES.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            rule = Rule(
                workspace_id=workspace.id,
                directory_ids=body.directory_ids,
                application_ids=body.application_ids,
                active=body.active,
                when=body.when,
                then=body.then,
                type=body.type,
                created_by=current_user.email,
            )
            irule = rule_store.insert(
                rule=rule,
                tx_context=tx_context,
            )
            return irule
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
            detail = e.detail if hasattr(e, "detail") else str(e)
            raise HTTPException(status_code=status_code, detail=detail)


@router.get("/{rule_id}", response_model=Rule, response_model_exclude_none=True)
def get(
    rule_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    rule_store: RuleStore = Depends(get_service(RuleStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.READ_RULES.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        rule = rule_store.get_by_id(
            rule_id=rule_id, workspace_id=workspace.id, tx_context=tx_context
        )
        if not rule:
            raise HTTPException(status_code=404, detail="rule not found")
        return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    rule_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    rule_store: RuleStore = Depends(get_service(RuleStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_RULES.value])),
):
    with SQLAlchemyTransactionContext().manage() as tx_context:
        rule_store.delete(
            rule_id=rule_id,
            workspace_id=workspace.id,
            tx_context=tx_context,
        )


class RulePatchOperation(PatchOperation):
    mutable_fields = RULE_MUTABLE_FIELDS


RuleJsonPatchDocument = JsonPatchDocument[RulePatchOperation]


@router.patch(
    "/{rule_id}",
    response_model=Rule,
    response_model_exclude_none=True,
)
async def update_rule(
    body: RuleJsonPatchDocument,
    rule_id: str,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    rule_store: RuleStore = Depends(get_service(RuleStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.UPDATE_RULES.value])),
):
    try:
        with SQLAlchemyTransactionContext().manage() as tx_context:
            rule = rule_store.get_by_id(
                rule_id=rule_id, workspace_id=workspace.id, tx_context=tx_context
            )
            if not rule:
                raise HTTPException(status_code=404, detail="rule not found")

            rule_dict = rule.model_dump()
            body_dict = body.model_dump()
            patch = jsonpatch.JsonPatch(body_dict["patch"])
            rule_updated_dict = patch.apply(rule_dict)
            rule_updated = Rule(**rule_updated_dict)
            ur = rule_store.update(rule=rule_updated, tx_context=tx_context)
            return ur
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


class RuleList(PaginatedListBase):
    items: List[PartialRule]


@router.get("", response_model=RuleList, response_model_exclude_none=True)
async def list(
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    list_params: dict = Depends(pagination_params),
    rule_store: RuleStore = Depends(get_service(RuleStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.READ_RULES.value])),
):
    limit = list_params.get("limit", 10)
    offset = list_params.get("offset", 0)
    projection = list_params.get("projection", None)
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            items, count = rule_store.list(
                workspace_id=workspace.id,
                tx_context=tx_context,
                limit=limit,
                offset=offset,
                projection=projection,
            )
            return RuleList(
                items=items,
                offset=offset,
                total=count,
            )
        except ValidationError as e:
            raise HTTPException(status_code=422, detail=e.errors())
