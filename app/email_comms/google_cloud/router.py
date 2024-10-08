import base64
import json

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, ConfigDict

from app.email_comms.google_cloud.gmail_utils import gmail_authenticate, respond
from app.models_stores import WorkspaceStore
from app.services import get_service


class EmailNotification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: str  # Base64 encoded email message
    messageId: str  # Unique identifier for the message
    publishTime: str  # Time the message was published


class WebhookNotification(BaseModel):
    message: EmailNotification
    subscription: str


router = APIRouter(
    prefix="/google_cloud", tags=["google_cloud"], include_in_schema=False
)


async def respond_to_email(notif: WebhookNotification):
    global history_id
    service = gmail_authenticate()
    msg_body = json.loads(base64.urlsafe_b64decode(notif.message.data).decode("utf-8"))
    # request a list of all the messages
    histories = (
        service.users().history().list(userId="me", startHistoryId=history_id).execute()
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
            .get(userId="me", id=msg["message"]["id"])
            .execute()
        )
        await respond(msg_body["emailAddress"], full_msg, service)

    new_history_id = msg_body["historyId"]
    history_id = new_history_id


@router.post("/events")
async def endpoint(body: WebhookNotification, background_tasks: BackgroundTasks):
    background_tasks.add_task(respond_to_email, notif=body)
    return {"acknowledged": True}


class InstallRequest(BaseModel):
    project_id: str
    topic_id: str
    subscription_id: str
    email_address: str
    client_id: str
    client_secret: str


@router.get("/install")
async def install(
    body: InstallRequest,
    workspace_store: WorkspaceStore = Depends(get_service(WorkspaceStore)),
):
    # auth with the provided credentials
    # start watch
    # install the gmail address to the workspace
    return {"message": "Install"}


def register(app):
    app.include_router(router)
