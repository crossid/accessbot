from slack_sdk import WebClient

from app.models import User
from app.services import factory_conversation_store
from app.slack.store_sql import sql_installation_store as installation_store
from app.sql import SQLAlchemyTransactionContext

from .iface import TicketInterface


class SlackImpl(TicketInterface):
    def __init__(self) -> None:
        pass

    def create_ticket(
        self,
        content: str,
        owner: User,
        requester: User,
        role_name: str,
        access: str,
        conv_summary: str,
        conversation_id: str,
        workspace_id: str,
    ):
        if owner is None:
            return

        conv_store = factory_conversation_store()
        with SQLAlchemyTransactionContext().manage() as tx_context:
            conv = conv_store.get_by_id(
                workspace_id=workspace_id,
                conversation_id=conversation_id,
                tx_context=tx_context,
            )
        reqCtx = conv.context
        bot = installation_store.find_bot(
            enterprise_id=reqCtx.get("enterprise_id", None),
            team_id=reqCtx.get("team_id", None),
        )
        bot_token = bot.bot_token if bot else None
        if not bot_token:
            Exception("Bot token not found")
        client = WebClient(token=bot_token)
        slack_requester = client.users_lookupByEmail(email=requester.email)
        requester_channel = slack_requester.data["user"]["id"]
        slack_owner_response = client.users_lookupByEmail(email=owner.email)
        resp_channel = slack_owner_response.data["user"]["id"]

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"You have a new request:\n*{requester.full_name}- Role Request*",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Role Name:*\n{role_name}\n*Access:*\n{access}\n*Summary:*\n{conv_summary}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Approve"},
                        "style": "primary",
                        "value": f"{role_name}||{requester.email}",
                        "action_id": "approve_request",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Deny"},
                        "style": "danger",
                        "value": f"{role_name}||{requester.email}",
                        "action_id": "deny_request",
                    },
                ],
            },
        ]

        metadata = {
            "event_type": "role_requested",
            "event_payload": {
                "requested_role": role_name,
                "requester_id": requester.id,
                "requester_email": requester.email,
                "conversation_id": conversation_id,
                "workspace_id": workspace_id,
                "requester_channel": requester_channel,
            },
        }

        client.chat_postMessage(
            channel=resp_channel, text=content, blocks=blocks, metadata=metadata
        )
