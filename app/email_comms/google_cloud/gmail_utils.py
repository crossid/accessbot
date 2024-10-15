import base64
import logging
import os
import re
from email.message import EmailMessage
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from pydantic import BaseModel

from app.consts import COMMUNICATION_CHANNEL_CONFIG_KEY
from app.models import Conversation, ConversationStatuses, Workspace
from app.services import factory_conversation_store, factory_user_store

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def gmail_authenticate(**kwargs):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("./tmp/token.json"):
        creds = Credentials.from_authorized_user_file("./tmp/token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "./tmp/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("./tmp/token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def start_watch(user_id: str, project_id: str, topic_id: str, service):
    request = {
        "labelIds": ["INBOX"],
        "topicName": f"projects/{project_id}/topics/{topic_id}",
        "labelFilterBehavior": "INCLUDE",
    }

    response = service.users().watch(userId=user_id, body=request).execute()
    # return {"historyId": response["historyId"], "expiration": response["expiration"]}
    return response


def decode_payload(payload):
    if payload["mimeType"] == "text/plain":
        data = payload["body"]["data"]
        text = base64.urlsafe_b64decode(data).decode("utf-8")
        return text
    elif payload["mimeType"] == "multipart/alternative":
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain":
                data = part["body"]["data"]
                text = base64.urlsafe_b64decode(data).decode("utf-8")
                return text
    return None


def create_message(sender, to, subject, message_text, thread_id=None, message_id=None):
    message = EmailMessage()
    message.set_content(message_text)
    message["To"] = to
    message["From"] = sender
    message["Subject"] = subject
    if message_id:
        message["References"] = message_id
        message["In-Reply-To"] = message_id

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    msg = {"raw": encoded_message}
    if thread_id:
        msg["threadId"] = thread_id
    return msg


async def generate_response(
    body: str, ws: Workspace, thread_id: str, user_email: str, tx_context
):
    user_store = factory_user_store()
    user = user_store.get_by_email(email=user_email)
    if user is None:
        return f"Hi, {user_email}, please register yourself so we can assist you."

    conversation_store = factory_conversation_store()
    conversation = conversation_store.get_by_external_id(
        workspace_id=ws.id, external_id=thread_id, tx_context=tx_context
    )
    if conversation is None:
        conversation = Conversation(
            assignee=user_email,
            workspace_id=ws.id,
            external_id=thread_id,
            context={COMMUNICATION_CHANNEL_CONFIG_KEY: "email"},
        )
        conversation = conversation_store.insert(
            conversation=conversation, tx_context=tx_context
        )
        logger.info("conversation %s created from gmail communication", conversation.id)
    elif conversation.status != ConversationStatuses.active:
        return "This conversation has ended, please start a new one."

    from app.llm.conversation import make_conversation

    result = await make_conversation(
        current_user=user, conversation=conversation, input=body, tx_context=tx_context
    )
    return result["output"]


class MsgPayload(BaseModel):
    body: str
    subject: str
    thread_id: str
    message_id: str
    sender: str


EMAIL_PATTERN = r"<([^>]+)>"


def get_msg_payload(msg: dict[str, Any]) -> MsgPayload:
    # Get value of 'payload'
    payload = msg["payload"]
    headers = payload["headers"]
    thread_id = msg["threadId"]
    # Look for Subject and Sender Email in the headers
    for d in headers:
        if d["name"] == "Subject":
            subject = d["value"]
        if d["name"] == "From":
            sender = d["value"]
        if d["name"] == "Message-ID":
            message_id = d["value"]

    match = re.search(EMAIL_PATTERN, sender)
    _sender = match.group(1) if match else sender

    return MsgPayload(
        body=decode_payload(payload),
        subject=subject,
        thread_id=thread_id,
        message_id=message_id,
        sender=_sender,
    )


async def create_response(
    email_address: str, ws: Workspace, msg_payload: MsgPayload, tx_context
) -> str:
    try:
        # do not reply to self
        if msg_payload.sender == email_address:
            raise Exception("Cannot reply to self")

        # sender_domain = sender.split("@")[-1]
        # email_domain = email_address.split("@")[-1]
        # if sender_domain != email_domain:
        #     raise Exception("Sender and receiver email domains do not match")

        if msg_payload.body is None:
            return "Cannot process email with no body"

        msg_body = await generate_response(
            body=msg_payload.body,
            ws=ws,
            thread_id=msg_payload.thread_id,
            tx_context=tx_context,
            user_email=msg_payload.sender,
        )

        return msg_body
    except Exception as e:
        return f"There was an error responding to your email: {str(e)}. Please notify a system administrator."


async def respond(
    service, sender, to, subject, message_text, thread_id=None, message_id=None
):
    reply_msg = create_message(
        sender=sender,
        to=to,
        subject=subject,
        message_text=message_text,
        thread_id=thread_id,
        message_id=message_id,
    )

    message = service.users().messages().send(userId=sender, body=reply_msg).execute()
    return message
