from fastapi import APIRouter

from app.health.route import healthCheckRoute
from app.health.service import HealthCheckFactory
from app.health.sqlalchemy_service import HealthCheckSQL
from app.models_facade_sql import ORG_TABLE_NAME
from app.sql import engine

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
)

_healthChecks = HealthCheckFactory()
_healthChecks.add(
    HealthCheckSQL(
        # The name of the object for your reference
        alias="postgresdb",
        engine=engine,
        # The Table that we will run a count method against.
        table=ORG_TABLE_NAME,
        tags=("postgres", "db"),
    )
)

router.add_api_route("/health", endpoint=healthCheckRoute(factory=_healthChecks))
