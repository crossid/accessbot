from fastapi import APIRouter, Depends

from app.authz import Permissions, is_admin_or_has_scopes
from app.email_comms.consts import ALL_COMM_TYPES, COMM_TYPE_GMAIL
from app.email_comms.google_cloud.gmail_comm import router as gmail_comm_router
from app.email_comms.google_cloud.gmail_utils import gmail_authenticate, start_watch
from app.models_stores import WorkspaceStore
from app.services import get_service
from app.sql import SQLAlchemyTransactionContext

router = APIRouter(
    prefix="/email_communication", tags=["google_cloud"], include_in_schema=False
)


@router.get("/watch")
async def watch(
    workspace_store: WorkspaceStore = Depends(get_service(WorkspaceStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.ADMIN.value])),
):
    all_comm_types_text = "','".join(ALL_COMM_TYPES)
    query = f"config::jsonb -> 'access_requests_method' ->> 'type' IN ('{all_comm_types_text}')"

    # start watch for all workspaces with email_communication enabled
    with SQLAlchemyTransactionContext().manage() as tx_context:
        workspaces, _ = workspace_store.list(
            tx_context, limit=100, filters={"__text__": query}
        )

        for workspace in workspaces:
            arm = workspace.config.get("access_requests_method", {})
            if arm.get("type") == COMM_TYPE_GMAIL:
                arm_config = arm.get("config", {})
                service = gmail_authenticate()
                watch_resp = start_watch(
                    user_id=arm_config["email_address"],
                    project_id=arm_config["project_id"],
                    topic_id=arm_config["topic_id"],
                    service=service,
                )
                arm_config["history_id"] = watch_resp["historyId"]
                workspace.config["access_requests_method"]["config"] = arm_config
                workspace_store.update(workspace, tx_context)


router.include_router(gmail_comm_router)


def register(app):
    app.include_router(router)
