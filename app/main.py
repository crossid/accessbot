import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.routers import internal, org
from app.sql import create_tables

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
app.include_router(api)
