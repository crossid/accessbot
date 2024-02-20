from sqlalchemy import create_engine

from app.models_facade_sql import OrgFacadeSQL

from .settings import settings

CONNECT_TIMEOUT = 10

engine = create_engine(
    settings.DB_URI,
    echo=True,
    # connect_args={"connect_timeout": 10},
)


org_facade = OrgFacadeSQL(engine=engine)


def create_tables():
    org_facade.create_tables()
