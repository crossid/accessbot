from slack_sdk.oauth.installation_store.sqlalchemy import SQLAlchemyInstallationStore
from slack_sdk.oauth.state_store.sqlalchemy import SQLAlchemyOAuthStateStore

from app.models_stores_sql import metadata

from ..settings import settings
from ..sql import sqlalchemy_engine

sql_installation_store = SQLAlchemyInstallationStore(
    engine=sqlalchemy_engine, client_id=settings.SLACK_CLIENT_ID
)

sql_installation_store.metadata = metadata
sql_installation_store.bots = sql_installation_store.build_bots_table(
    metadata=metadata, table_name=sql_installation_store.default_bots_table_name
)
sql_installation_store.installations = sql_installation_store.build_installations_table(
    metadata=metadata,
    table_name=sql_installation_store.default_installations_table_name,
)

state_store = SQLAlchemyOAuthStateStore(
    engine=sqlalchemy_engine, expiration_seconds=600
)
state_store.metadata = metadata
state_store.oauth_states = state_store.build_oauth_states_table(
    metadata=metadata, table_name=state_store.default_table_name
)

_metadata_for_migrations_ = metadata
