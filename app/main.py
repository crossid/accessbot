import logging
from contextlib import asynccontextmanager

import injector
from fastapi import APIRouter, FastAPI

from .injector_extensions_module import ExtensionModule
from .injector_main_module import MainModule
from .services import set_service_registry

from .routers import content, conversation, internal, org
from .slack.store_sql import init_sql
from .sql import create_tables

logger = logging.getLogger(__name__)

service_registry = injector.Injector([MainModule(), ExtensionModule()])
set_service_registry(service_registry)


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
api.include_router(conversation.router)
api.include_router(content.router)
app.include_router(api)

# extensions
from .slack.router import register as slack_register  # noqa

slack_register(app)
