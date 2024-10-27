from slack_sdk import WebClient

from app.i18n import i18n
from app.llm.tools.create_ticket.iface import TicketInterface
from app.models import User
from app.services import factory_conversation_store
from app.slack.store_sql import sql_installation_store as installation_store
from app.sql import SQLAlchemyTransactionContext


class SlackImpl(TicketInterface):
    def __init__(self) -> None:
        pass

    def create_ticket(
        self,
        content: str,
        owner: User,
        requester: User,
        conv_summary: str,
        conversation_id: str,
        workspace_id: str,
        app_name: str,
        conv_lang: str,
        **kwargs,
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

        i = i18n(lang=conv_lang)
        formatted_kwargs = "; ".join(
            [f"{i.t(key)}: {value}" for key, value in kwargs.items()]
        )

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{i.t('request_waiting').capitalize()}:\n*{requester.full_name}*",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*{i.t('app_name').capitalize()}:*\n{app_name}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*{i.t('summary').capitalize()}:*\n{conv_summary}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*{i.t('my_recommendation').capitalize()}:*\n{formatted_kwargs}",
                    },
                ],
            },
        ]

        metadata = {
            "event_type": "role_requested",
            "event_payload": {
                "requester_id": requester.id,
                "requester_email": requester.email,
                "conversation_id": conversation_id,
                "workspace_id": workspace_id,
                "requester_channel": requester_channel,
                "channel_id": resp_channel,
            },
        }

        resp = client.chat_postMessage(
            channel=resp_channel, text=content, blocks=blocks, metadata=metadata
        )

        thread = resp.data.get("ts", None)
        client.chat_postMessage(
            channel=resp_channel,
            thread_ts=thread,
            text=i.t("approval_q").capitalize(),
        )

        return thread
