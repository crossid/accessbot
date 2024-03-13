from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings

from ..settings import settings
from .actions_approve_deny import handle_approve, handle_deny
from .event_app_home_opened import handle_learn_more, update_home_tab
from .event_message import answer
from .store_sql import sql_installation_store, state_store

oauth_settings = OAuthSettings(
    client_id=settings.SLACK_CLIENT_ID,
    client_secret=settings.SLACK_CLIENT_SECRET,
    scopes=[
        "app_mentions:read",
        "channels:read",
        "chat:write",
        "im:history",
        "im:read",
        "im:write",
        "incoming-webhook",
        "mpim:read",
        "users:read",
        "users:read.email",
    ],
    installation_store=sql_installation_store,
    state_store=state_store,
)

app = App(signing_secret=settings.SLACK_SIGNING_SECRET, oauth_settings=oauth_settings)
app.event("message")(answer)
app.event("app_home_opened")(update_home_tab)
app.action("learn_more")(handle_learn_more)
app.action("approve_request")(handle_approve)
app.action("deny_request")(handle_deny)
