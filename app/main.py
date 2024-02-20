import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import internal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug("Starting")
    yield
    logger.debug("Stopping")


app = FastAPI(lifespan=lifespan)
app.include_router(internal.router)
