import asyncio

from slack_sdk import WebClient

from app.llm.conversation import make_conversation
from app.models import AccessRequest, StatusEnum
from app.sql import SQLAlchemyTransactionContext

from ..services import request_facade, user_store
from .app import app


@app.event("message")
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

        user = user_store.get_by_email(email=slack_user_email)
        if user is None:
            # TODO redirect the user to the app's about tab (see https://api.slack.com/reference/deep-linking)
            say(
                text=f"Hi {slack_user_email}, go to the about page and register yourself!"
            )
            return

        orgs = user_store.list_orgs_for_user(user_id=user.id)
        if len(orgs) == 0:
            say(
                text=f"Hi {slack_user_email}, you are not part of any organization yet."
            )
            return
        # TODO: consider letting the user choose the org to work with in Slack
        org = orgs[0]
        access_request: AccessRequest = None
        with SQLAlchemyTransactionContext().manage() as tx_context:
            access_request = request_facade.get_by_external_id(
                org_id=org.id, external_id=thread_ts, tx_context=tx_context
            )

        if access_request is None:
            request_ctx = {}
            team_id = context.get("team_id", None)
            if team_id is not None:
                request_ctx["team_id"] = team_id
            enterprise_id = context.get("enterprise_id", None)
            if enterprise_id is not None:
                request_ctx["enterprise_id"] = enterprise_id

            ar = AccessRequest(
                requestee_id=user.id,
                org_id=org.id,
                external_id=thread_ts,
                context=request_ctx,
            )
            with SQLAlchemyTransactionContext().manage() as tx_context:
                access_request = request_facade.insert(req=ar, tx_context=tx_context)
                logger.info("request %s created from slack", access_request.id)
        elif access_request.status == StatusEnum.submitted:
            say(
                text="This conversation is already submitted, please start a new one.",
                thread_ts=thread_ts,
            )
            return
        elif access_request.status == StatusEnum.completed:
            say(
                text="This conversation is ended, please start a new one.",
                thread_ts=thread_ts,
            )
            return

        with SQLAlchemyTransactionContext().manage() as tx_context:
            co_routine = make_conversation(
                current_user=user,
                request=access_request,
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
        logger.error(f"Error answering message: {e}")