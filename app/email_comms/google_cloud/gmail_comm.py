import base64
import json
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, ConfigDict

from app.auth import get_current_workspace
from app.authz import Permissions, is_admin_or_has_scopes
from app.consts import EMAIL_CONFIG_KEY
from app.email_comms.consts import COMM_TYPE_GMAIL
from app.email_comms.google_cloud.gmail_utils import (
    create_response,
    get_msg_payload,
    gmail_authenticate,
    respond,
    start_watch,
)
from app.models import Workspace
from app.models_stores import WorkspaceStore
from app.services import get_service
from app.sql import SQLAlchemyTransactionContext
from app.vault_utils import resolve_ws_config_secrets

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/google_cloud", tags=["google_cloud"], include_in_schema=False
)


class EmailNotification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: str  # Base64 encoded email message
    messageId: str  # Unique identifier for the message
    publishTime: str  # Time the message was published


class WebhookNotification(BaseModel):
    message: EmailNotification
    subscription: str


def get_ws_of_email(
    ws_store: WorkspaceStore, email_address: str, tx_context
) -> Workspace:
    query = f"config::jsonb -> 'email' ->> 'type' = '{COMM_TYPE_GMAIL}' AND config::jsonb -> 'email' -> 'config' ->> 'email_address' = '{email_address}'"
    workspaces, sum = ws_store.list(tx_context, limit=1, filters={"__text__": query})
    if sum == 0:
        raise Exception(f"Workspace with email {email_address} not found")

    return workspaces[0]


async def respond_to_email(notif: WebhookNotification, ws_store: WorkspaceStore):
    msg_body = json.loads(base64.urlsafe_b64decode(notif.message.data).decode("utf-8"))
    email_address = msg_body["emailAddress"]

    history_id = ""
    with SQLAlchemyTransactionContext().manage() as tx_context:
        try:
            workspace = get_ws_of_email(ws_store, email_address, tx_context)
            resolved_config = resolve_ws_config_secrets(
                workspace_id=workspace.id,
                config=workspace.config[EMAIL_CONFIG_KEY]["config"],
            )
            history_id = workspace.config["access_requests_method"]["config"][
                "history_id"
            ]

            new_history_id = msg_body["historyId"]
            workspace.config["access_requests_method"]["config"][
                "history_id"
            ] = new_history_id
            ws_store.update(workspace, tx_context)
        except Exception as e:
            logger.fatal(f"{str(e)}")
            return

        service = gmail_authenticate(**resolved_config)

        # request a list of all the messages
        histories = (
            service.users()
            .history()
            .list(userId=email_address, startHistoryId=history_id)
            .execute()
        )

        messages = []
        if "history" in histories:
            for history in histories["history"]:
                if "messagesAdded" in history:
                    messages.extend(history["messagesAdded"])

        for msg in messages:
            full_msg = (
                service.users()
                .messages()
                .get(userId=email_address, id=msg["message"]["id"])
                .execute()
            )
            try:
                msg_payload = get_msg_payload(full_msg)
                txt_resp = await create_response(
                    email_address=email_address,
                    ws=workspace,
                    tx_context=tx_context,
                    msg_payload=msg_payload,
                )
            except Exception as e:
                logger.error(f"Error responding to email: {str(e)}")
                txt_resp = f"An error occurred while processing your request.\n\n{str(e)} \n\nPlease try again later."

            try:
                await respond(
                    service=service,
                    sender=email_address,
                    to=msg_payload.sender,
                    subject=f"Re: {msg_payload.subject}",
                    message_text=txt_resp,
                    thread_id=msg_payload.thread_id,
                    message_id=msg_payload.message_id,
                )
            except Exception as e:
                logger.error(f"Error responding to email: {str(e)}")


@router.post("/events")
async def endpoint(
    body: WebhookNotification,
    background_tasks: BackgroundTasks,
    workspace_store: WorkspaceStore = Depends(get_service(WorkspaceStore)),
):
    background_tasks.add_task(respond_to_email, notif=body, ws_store=workspace_store)
    return {"acknowledged": True}


class InstallRequest(BaseModel):
    project_id: str
    topic_id: str
    email_address: str
    client_id: str
    client_secret: str


@router.post("/install")
async def install(
    body: InstallRequest,
    workspace: Annotated[Workspace, Depends(get_current_workspace)],
    workspace_store: WorkspaceStore = Depends(get_service(WorkspaceStore)),
    _=Depends(is_admin_or_has_scopes(scopes=[Permissions.ADMIN.value])),
):
    # auth with the provided credentials
    service = gmail_authenticate()
    # start watch
    watch_resp = start_watch(
        user_id=body.email_address,
        project_id=body.project_id,
        topic_id=body.topic_id,
        service=service,
    )
    # install the gmail address to the workspace
    workspace.config[EMAIL_CONFIG_KEY] = {
        "type": COMM_TYPE_GMAIL,
        "config": {
            "email_address": body.email_address,
            "client_id": body.client_id,
            "client_secret": body.client_secret,
        },
    }
    workspace.config["access_requests_method"] = {
        "type": COMM_TYPE_GMAIL,
        "config": {
            "project_id": body.project_id,
            "topic_id": body.topic_id,
            "history_id": watch_resp["historyId"],
        },
    }

    with SQLAlchemyTransactionContext().manage() as tx_context:
        workspace_store.update(workspace=workspace, tx_context=tx_context)

    return {
        EMAIL_CONFIG_KEY: workspace.config[EMAIL_CONFIG_KEY],
        "access_requests_method": workspace.config["access_requests_method"],
    }
