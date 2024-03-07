from fastapi import APIRouter

from ..health.route import healthCheckRoute
from ..health.service import HealthCheckFactory
from ..health.sqlalchemy_service import HealthCheckSQL
from ..models_stores_sql import ORG_TABLE_NAME
from ..sql import sqlalchemy_engine as engine

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)

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
