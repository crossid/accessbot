def update_home_tab(client, event, logger):
    try:
        # views.publish is the method that your app uses to push a view to the Home tab
        client.views_publish(
            # the user that opened your app's app home
            user_id=event["user"],
            # the view object that appears in the app home
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "👋 Welcome to the _AccessBot_",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "The AccessBot allows you to request access to various apps.",
                        },
                        "accessory": {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Learn More"},
                            "action_id": "learn_more",
                        },
                    },
                ],
            },
        )

    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


def handle_learn_more(ack, body, client):
    # Acknowledge the action
    ack()

    try:
        # Call views.open with the built-in client
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "title": {"type": "plain_text", "text": "Get Started"},
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Click on the _AccessBot_ in Apps and start interacting with the Bot.",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Simply ask for the access you need to get recommendations.",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Once you approve the recommendation, the bot will request the access for you.",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "If approval is required, the bot will send an approval request to the data owner.",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Once approved, your access will be automatically provisioned, no worries you'l get notified!",
                        },
                    },
                ],
                "close": {"type": "plain_text", "text": "Close"},
            },
        )
    except Exception as e:
        print(f"Error opening modal: {e}")
