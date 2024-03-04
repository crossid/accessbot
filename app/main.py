import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from .routers import content, internal, org, request
from .sql import create_tables

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Starting")
    create_tables()
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
