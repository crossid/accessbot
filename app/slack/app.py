from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings

from app.settings import settings

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
