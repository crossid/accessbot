import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from .routers import content, internal, org, request
from .slack.store_sql import init_sql
from .sql import create_tables

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Starting")
    create_tables()
    # extensions
    init_sql()
    yield
    logger.debug("Stopping")


app = FastAPI(lifespan=lifespan)
app.include_router(internal.router)

# api routers
api = APIRouter(prefix="/api")
api.include_router(org.router)
api.include_router(request.router)
api.include_router(content.router)
app.include_router(api)

# extensions
from app.slack.router import register as slack_register  # noqa

slack_register(app)
# api.include_router(slack_router)
