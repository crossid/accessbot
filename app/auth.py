from fastapi import Request

from app.models import User


# TODO implement
async def get_current_active_user(request: Request) -> User:
    return User(id="123", email="john@acme.io", full_name="John Doe", disabled=False)
