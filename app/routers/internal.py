from fastapi import APIRouter

from app.health.route import healthCheckRoute
from app.health.service import HealthCheckFactory

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
)

_healthChecks = HealthCheckFactory()
# TODO add services checks here
# _healthChecks.add(
# HealthCheckSQL(
#     # The name of the object for your reference
#     alias="postgresdb",
#     session=get_session(),
#     # The Table that we will run a count method against.
#     table=Org.__tablename__,
#     tags=("postgres", "db"),
# )
# )

router.add_api_route("/health", endpoint=healthCheckRoute(factory=_healthChecks))
