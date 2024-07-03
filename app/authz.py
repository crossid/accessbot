from enum import Enum
from typing import Annotated, List

from fastapi import Depends, HTTPException, status

from app.auth import get_current_active_user, get_optional_current_workspace

from .models import CurrentUser, Workspace


class Permissions(Enum):
    ADMIN = "admin"
    READ_AUTH_METHODS = "read:auth-methods"
    UPDATE_AUTH_METHODS = "update:auth-methods"
    DELETE_AUTH_METHODS = "delete:auth-methods"
    UPDATE_WORKSPACES = "update:workspaces"
    READ_WORKSPACES = "read:workspaces"
    DELETE_WORKSPACES = "delete:workspaces"
    CREATE_WORKSPACES = "create:workspaces"
    UPDATE_CONVERSATIONS = "update:conversations"
    READ_CONVERSATIONS = "read:conversations"
    UPDATE_CONTENT = "update:content"
    READ_CONTENT = "read:content"
    DELETE_CONTENT = "delete:content"
    UPDATE_DOMAINS = "update:domains"
    DELETE_DOMAINS = "delete:domains"
    UPDATE_DIRECTORIES = "update:directories"
    READ_DIRECTORIES = "read:directories"
    DELETE_DIRECTORIES = "delete:directories"
    UPDATE_APPLICATIONS = "update:applications"
    READ_APPLICATIONS = "read:applications"
    DELETE_APPLICATIONS = "delete:applications"
    UPDATE_SECRETS = "update:secrets"
    DELETE_SECRETS = "delete:secrets"
    READ_SECRETS = "read:secrets"
    READ_RULES = "read:rules"
    UPDATE_RULES = "update:rules"


class AdminOrScopes:
    current_user_email: str
    is_admin: bool
    has_scopes: bool

    def __init__(self, is_admin: bool, has_scopes: bool, current_user_email: str):
        self.is_admin = is_admin
        self.has_scopes = has_scopes
        self.current_user_email = current_user_email


# raises an error if insufficient scopes
def is_admin_or_has_scopes(
    scopes: List[str],
):
    def _check(
        current_user: Annotated[CurrentUser, Depends(get_current_active_user)],
        workspace: Annotated[Workspace, Depends(get_optional_current_workspace)],
    ) -> AdminOrScopes:
        result = AdminOrScopes(False, False, current_user.email)

        if workspace is not None and current_user.email == workspace.created_by:
            result.is_admin = True
        elif Permissions.ADMIN.value in current_user.scopes:
            result.is_admin = True

        if all(scope in current_user.scopes for scope in scopes):
            result.has_scopes = True

        if result.is_admin is False and result.has_scopes is False:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="insufficient scopes"
            )

        return result

    return _check
