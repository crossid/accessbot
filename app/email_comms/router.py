from fastapi import APIRouter, Depends

from app.authz import Permissions, is_admin_or_has_scopes
from app.consts import EMAIL_CONFIG_KEY
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
    query = f"config::jsonb -> 'email' ->> 'type' IN ('{all_comm_types_text}')"
    response = {}
    # start watch for all workspaces with email_communication enabled
    with SQLAlchemyTransactionContext().manage() as tx_context:
        workspaces, _ = workspace_store.list(
            tx_context, limit=100, filters={"__text__": query}
        )

        for workspace in workspaces:
            email_config = workspace.config.get(EMAIL_CONFIG_KEY, {})
            if email_config.get("type") == COMM_TYPE_GMAIL:
                gm_config = email_config.get("config", {})
                service = gmail_authenticate()
                watch_resp = start_watch(
                    user_id=gm_config["email_address"],
                    project_id=gm_config["project_id"],
                    topic_id=gm_config["topic_id"],
                    service=service,
                )
                gm_config["history_id"] = watch_resp["historyId"]
                workspace.config[EMAIL_CONFIG_KEY]["config"] = gm_config
                workspace_store.update(workspace, tx_context)
                response[workspace.id] = watch_resp

    return response


router.include_router(gmail_comm_router)


def register(app):
    app.include_router(router)
