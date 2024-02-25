import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import jwt
import requests
from cachetools import TTLCache, cached
from fastapi import HTTPException, Request

from app.models import CurrentUser
from app.settings import settings

log = logging.getLogger(__name__)


class AuthAPI(ABC):
    @abstractmethod
    def authenticate(request: Request) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_current_user(request: Request) -> Optional[CurrentUser]:
        pass


class OAuth2Impl(AuthAPI):
    def __init__(self):
        if not jwt.algorithms.has_crypto:
            raise Exception(
                "No crypto support for JWT, please install the cryptography dependency"
            )
        resp = requests.get(settings.OAUTH2_OPENID_CONFIGURATION)
        if resp.status_code != 200:
            raise Exception("Could not fetch openid configuration")
        self._oauth_configuration = resp.json()

    def _get_token_from_request(self, request: Request) -> str:
        authorization_header = request.headers.get("Authorization")

        if not authorization_header:
            raise HTTPException(
                status_code=401, detail="Authorization header is missing"
            )

        _, token = authorization_header.split(" ")

        return token

    def authenticate(self, request: Request) -> dict[str, Any]:
        access_token = self._get_token_from_request(request)
        try:
            jwks_client = jwt.PyJWKClient(
                self._oauth_configuration["jwks_uri"], cache_jwk_set=True, lifespan=360
            )
            signing_key = jwks_client.get_signing_key_from_jwt(access_token)
            data = jwt.decode(
                access_token,
                key=signing_key.key,
                algorithms=["RS256"],
                issuer=self._oauth_configuration["issuer"],
                audience=settings.OAUTH2_AUDIENCE,
                # should be default, but just to be doubly clear
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )
            log.debug("decoded token: ", data)
            return data
        except jwt.exceptions.PyJWTError as e:
            log.info("Token is invalid: %s", e)
            raise HTTPException(status_code=401, detail="token is invalid")

    @cached(cache=TTLCache(maxsize=1000, ttl=300))
    def fetch_userinfo_by_access_token(self, access_token: str) -> dict[str, Any]:
        try:
            data = requests.get(
                url=self._oauth_configuration["userinfo_endpoint"],
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return data.json()

        except Exception as err:
            raise HTTPException(status_code=401, detail=f"{err}")

    def get_current_user(self, request: Request, decoded_access_token: dict[str, Any]):
        access_token = self._get_token_from_request(request)
        user = self.fetch_userinfo_by_access_token(access_token)
        return CurrentUser.from_oauth2(user, decoded_access_token)


# factory method for AuthAPI
def create_auth_api() -> AuthAPI:
    return OAuth2Impl()


auth_api = create_auth_api()


def get_current_active_user(request: Request) -> Optional[CurrentUser]:
    try:
        decoded_token = auth_api.authenticate(request)
        return auth_api.get_current_user(request, decoded_token)
    except Exception:
        raise Exception("Not authenticated")


def factory_auth_api(request: Request) -> AuthAPI:
    return auth_api
