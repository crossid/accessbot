import asyncio
import copy

from slack_sdk import WebClient

from ..llm.conversation import make_conversation
from ..services import factory_conversation_store, factory_user_store
from ..sql import SQLAlchemyTransactionContext

processing_block = {
    "type": "context",
    "elements": [{"type": "mrkdwn", "text": "*Proccessing* :hourglass_flowing_sand:"}],
}


def approve_or_deny(
    ack, action, respond, logger, body, client: WebClient, approved: bool
):
    conv_text = "yes" if approved else "no"
    approved_or_denied = "approved" if approved else "denied"
    approving_or_denying = "approving" if approved else "denying"
    try:
        ack()
        message_payload = body["message"]["metadata"]["event_payload"]

        # respond with "processing" block
        blocks = body["message"]["blocks"]
        processing_blocks = copy.deepcopy(blocks)
        processing_blocks.pop()
        processing_blocks.append(processing_block)

        respond(
            replace_original=True,
            response_type="in_channel",
            text="Processing Request",
            blocks=processing_blocks,
        )

        # get current user
        slack_user = client.users_info(user=body["user"]["id"])
        slack_user_email = slack_user.data["user"]["profile"]["email"]
        user_store = factory_user_store()
        user = user_store.get_by_email(email=slack_user_email)

        with SQLAlchemyTransactionContext().manage() as tx_context:
            ws_id = message_payload["workspace_id"]
            # get conversation
            conv_id = message_payload["conversation_id"]
            conv_store = factory_conversation_store()
            conv = conv_store.get_by_external_id(
                workspace_id=ws_id, external_id=conv_id, tx_context=tx_context
            )

            co_routine = make_conversation(
                current_user=user,
                conversation=conv,
                input=conv_text,
                tx_context=tx_context,
            )
            _ = asyncio.new_event_loop().run_until_complete(co_routine)

        role_name = message_payload["requested_role"]
        requester = message_payload["requester_email"]

        respond(
            replace_original=True,
            response_type="in_channel",
            text=f"You {approved_or_denied} this request: [{role_name}] for [{requester}]",
        )

    except Exception as e:
        logger.error(f"Error approving request: {e}")
        # return original "approve/deny" block
        respond(
            replace_original=True,
            response_type="in_channel",
            text="Processing Request Ended",
            blocks=blocks,
        )
        # respond with an ephemeral error message
        respond(
            text=f"There was a problem {approving_or_denying} the request: {e}",
            replace_original=False,
        )


def handle_approve(ack, action, respond, logger, body, client: WebClient):
    approve_or_deny(
        ack=ack,
        action=action,
        respond=respond,
        logger=logger,
        body=body,
        client=client,
        approved=True,
    )


def handle_deny(ack, action, respond, logger, body, client):
    approve_or_deny(
        ack=ack,
        action=action,
        respond=respond,
        logger=logger,
        body=body,
        client=client,
        approved=False,
    )
