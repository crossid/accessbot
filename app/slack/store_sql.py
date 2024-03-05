from slack_sdk.oauth.installation_store.sqlalchemy import SQLAlchemyInstallationStore
from slack_sdk.oauth.state_store.sqlalchemy import SQLAlchemyOAuthStateStore

from ..settings import settings
from ..sql import sqlalchemy_engine

sql_installation_store = SQLAlchemyInstallationStore(
    engine=sqlalchemy_engine, client_id=settings.SLACK_CLIENT_ID
)
state_store = SQLAlchemyOAuthStateStore(
    engine=sqlalchemy_engine, expiration_seconds=600
)


def init_sql():
    sql_installation_store.metadata.create_all(sqlalchemy_engine)
    state_store.metadata.create_all(sqlalchemy_engine)
