# https://github.com/slackapi/bolt-python/blob/main/examples/fastapi/app.py
from fastapi import APIRouter, Request
from slack_bolt.adapter.fastapi import SlackRequestHandler

from .app import app as slack_app

router = APIRouter(prefix="/slack", tags=["slack"], include_in_schema=False)


handler = SlackRequestHandler(app=slack_app)


@router.post("/events")
async def endpoint(req: Request):
    return await handler.handle(req)


@router.get("/install")
async def install(req: Request):
    return await handler.handle(req)


@router.get("/oauth_redirect")
async def oauth_redirect(req: Request):
    return await handler.handle(req)


def register(app):
    app.include_router(router)
