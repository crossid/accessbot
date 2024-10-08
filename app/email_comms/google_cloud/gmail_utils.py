import base64
import os
from email.message import EmailMessage
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def gmail_authenticate():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def start_watch(project_id: str, topic_id: str):
    # Use the authenticated service
    service = gmail_authenticate()

    request = {
        "labelIds": ["INBOX"],
        "topicName": f"projects/{project_id}/topics/{topic_id}",
        "labelFilterBehavior": "INCLUDE",
    }

    response = service.users().watch(userId="me", body=request).execute()
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


def create_message(sender, to, subject, message_text, thread_id, message_id):
    message = EmailMessage()
    message.set_content(message_text)
    message["To"] = to
    message["From"] = sender
    message["Subject"] = subject
    message["References"] = message_id
    message["In-Reply-To"] = message_id
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    return {"raw": encoded_message, "threadId": thread_id}


async def respond(emailAddress: str, msg: dict[str, Any], service):
    try:
        # Get value of 'payload'
        payload = msg["payload"]
        headers = payload["headers"]

        # Look for Subject and Sender Email in the headers
        for d in headers:
            if d["name"] == "Subject":
                subject = d["value"]
            if d["name"] == "From":
                sender = d["value"]
            if d["name"] == "Message-ID":
                message_id = d["value"]

        # do not reply to self
        if sender == emailAddress:
            return

        body = decode_payload(payload)
        thread_id = msg["threadId"]

        # Create a reply message
        reply_msg = create_message(
            sender=emailAddress,
            to=sender,
            subject=f"Re: {subject}",
            message_text=body,
            thread_id=thread_id,
            message_id=message_id,
        )

        message = service.users().messages().send(userId="me", body=reply_msg).execute()
        return message
    except Exception:
        pass
