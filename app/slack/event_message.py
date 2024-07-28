import asyncio

from slack_sdk import WebClient

from ..llm.conversation import make_conversation
from ..models import Conversation, ConversationStatuses, Workspace
from ..models_stores import ConversationStore, UserStore
from ..services import factory_ws_store, service_registry
from ..sql import SQLAlchemyTransactionContext


def answer(client: WebClient, event, logger, say, context):
    """
    Handle the 'message' event from Slack and respond to the user.

    Args:
        client (WebClient): The Slack WebClient instance.
        event (dict): The event data received from Slack.
        logger: The logger instance for logging errors.
        say: The function to send a message back to Slack.
        context (dict): Additional context data.

    Event example:
    {
        'user': 'UC251A0RW',
        'type': 'message',
        'ts': '1709495579.183909',
        'client_msg_id': 'c8a3a83f-f7b0-409b-9d4a-9bff12e76f28',
        'text': 'hi',
        'team': 'TC29TGE7K',
        'blocks': [
            {
                'type': 'rich_text', 'block_id': 'a8bcU',
                'elements': [{'type': 'rich_text_section',
                'elements': [{'type': 'text', 'text': 'hi'}]}]}],
                'channel': 'D06MKUAUXHB', 'event_ts':'1709495579.183909', 'channel_type': 'im'
            }

    """
    try:
        # fetch sender user
        slack_user = client.users_info(user=event["user"])
        slack_user_email = slack_user.data["user"]["profile"]["email"]
        # thread id to reply to the message
        thread_ts = event.get("thread_ts", None) or event["ts"]

        user_store = service_registry().get(UserStore)
        user = user_store.get_by_email(email=slack_user_email)
        if user is None:
            # TODO redirect the user to the app's about tab (see https://api.slack.com/reference/deep-linking)
            say(
                text=f"Hi {slack_user_email}, go to the about page and register yourself!"
            )
            return

        workspaces = user_store.list_workspaces_for_user(user_id=user.id)
        if len(workspaces) == 0:
            say(text=f"Hi {slack_user_email}, you are not part of any workspace yet.")
            return
        # TODO: consider letting the user choose the ws to work with in Slack
        ws_ext_id = workspaces[0]
        ws_store = factory_ws_store()
        conversation: Conversation | None = None
        ws: Workspace | None = None
        conversation_store = service_registry().get(ConversationStore)
        with SQLAlchemyTransactionContext().manage() as tx_context:
            ws = ws_store.get_by_id(workspace_id=ws_ext_id, tx_context=tx_context)
            if ws is None:
                say(
                    text=f"We could not find workspace {ws_ext_id}", thread_ts=thread_ts
                )
                return

            conversation = conversation_store.get_by_external_id(
                workspace_id=ws.id, external_id=thread_ts, tx_context=tx_context
            )

        if conversation is None:
            conversation_ctx = {}
            team_id = context.get("team_id", None)
            if team_id is not None:
                conversation_ctx["team_id"] = team_id
            enterprise_id = context.get("enterprise_id", None)
            if enterprise_id is not None:
                conversation_ctx["enterprise_id"] = enterprise_id

            conversation = Conversation(
                assignee=user.email,
                workspace_id=ws.id,
                external_id=thread_ts,
                context=conversation_ctx,
            )
            with SQLAlchemyTransactionContext().manage() as tx_context:
                conversation = conversation_store.insert(
                    conversation=conversation, tx_context=tx_context
                )
                logger.info("conversation %s created from slack", conversation.id)
        elif conversation.status != ConversationStatuses.active:
            say(
                text="This conversation has ended, please start a new one.",
                thread_ts=thread_ts,
            )
            return

        with SQLAlchemyTransactionContext().manage() as tx_context:
            co_routine = make_conversation(
                current_user=user,
                conversation=conversation,
                input=event["text"],
                tx_context=tx_context,
            )
            result = asyncio.new_event_loop().run_until_complete(co_routine)
            say(
                blocks=[
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": result["output"]},
                    }
                ],
                thread_ts=thread_ts,
            )
    except Exception as e:
        import traceback

        say(
            f"Fatal bot error: {str(e)}. Please follow up with the system admin",
            thread_ts=thread_ts,
        )

        logger.error(f"Error answering message: {e}")
        logger.error(traceback.format_exc())
