from typing import Any, List, Self

import requests


def auth(host: str, auth_method_id, attributes: dict[str, Any]) -> str:
    headers = {"Authorization": "Bearer ", "Content-Type": "application/json"}
    data = {
        "command": "login",
        "attributes": attributes,
    }

    url = f"https://{host}/v1/auth-methods/{auth_method_id}:authenticate"
    resp = requests.post(
        url=url,
        json=data,
        headers=headers,
    )
    if resp.status_code <= 399:
        jresp = resp.json()
        return jresp["attributes"]["token"]
    else:
        raise ValueError(f"error: {resp.status_code}: {resp.text}")


# TODO: These tokens are good for a week, so think about longer caching.
# cache can't hash dict, so this is currently an issue
# @cached(cache=TTLCache(maxsize=1000, ttl=3600))
# def auth_with_cache(host: str, auth_method_id, attributes: dict[str, Any]) -> str:
#     return auth(host=host, auth_method_id=auth_method_id, attributes=attributes)


class ListResponse:
    _url: str
    _params: dict[str, Any]
    _headers: dict[str, str]
    items: List[dict[str, Any]]
    response_type: str
    list_token: str

    def __init__(
        self,
        url: str,
        headers: dict[str, str],
        params: dict[str, Any],
        resp: dict[str, Any],
    ) -> None:
        self._url = url
        self._params = params
        self._headers = headers
        self.response_type = resp["response_type"]
        self.list_token = resp.get("list_token", None)
        self.items = resp.get("items", [])

    def has_next(self) -> bool:
        return self.response_type != "complete"

    def get_next(self) -> Self:
        params = self._params.copy()
        if self.list_token is not None:
            params["list_token"] = self.list_token

        resp = requests.get(url=self._url, headers=self._headers, params=params)
        if resp.status_code <= 399:
            jResp = resp.json()
            return ListResponse(
                url=self._url, headers=self._headers, params=self._params, resp=jResp
            )

        else:
            raise ValueError(f"error: {resp.status_code}: {resp.text}")


class GetResponse:
    item: dict[str, Any]
    _headers: dict[str, str]

    def __init__(self, resp: dict[str, Any], headers: dict[str, str]) -> None:
        self.item = resp
        self._headers = headers


class Client:
    _access_token: str
    _host: str

    def __init__(self, host) -> None:
        self._host = host

    def auth(self, auth_method_id: str, attributes: dict[str, Any]):
        access_token = auth(
            host=self._host, auth_method_id=auth_method_id, attributes=attributes
        )
        self._access_token = access_token

    def set_token(self, access_token: str):
        self._access_token = access_token

    def _prepare_url(self, url: str) -> str:
        if not url.startswith("/"):
            url = f"/{url}"

        url = url.removeprefix("/v1")
        return f"https://{self._host}/v1{url}"

    def get_resource(
        self, url: str, params: dict[str, Any] | None = None
    ) -> GetResponse:
        if self._access_token is None:
            raise ValueError("access token must be set")

        _url = self._prepare_url(url)
        headers = {"Authorization": f"Bearer {self._access_token}"}
        resp = requests.get(url=_url, headers=headers, params=params)
        if resp.status_code <= 399:
            jResp = resp.json()
            return GetResponse(resp=jResp, headers=headers)
        else:
            raise ValueError(f"error: {resp.status_code}: {resp.text}")

    def list_resource(self, url: str, params: dict[str, Any]) -> ListResponse:
        if self._access_token is None:
            raise ValueError("access token must be set")

        resp = self.get_resource(url=url, params=params)
        return ListResponse(
            url=url, headers=resp._headers, params=params, resp=resp.item
        )

    def add_principal(self, user_id: str, role_id: str, version: int):
        url = f"https://{self._host}/v1/roles/{role_id}:add-principals"
        params = {}

        headers = {"Authorization": f"Bearer {self._access_token}"}
        body = {"version": version, "principal_ids": [user_id]}
        resp = requests.post(url=url, headers=headers, params=params, json=body)
        if resp.status_code <= 399:
            jResp = resp.json()
            return jResp
        else:
            raise ValueError(f"error: {resp.status_code}: {resp.text}")


def create_role_id(scope_name: str, role_id: str) -> str:
    return f"{scope_name}|{role_id}"


class broken_role_id:
    scope_name: str
    role_id: str

    def __init__(self, role_id: str) -> None:
        role_split = role_id.split("|")
        self.scope_name = role_split[0]
        self.role_id = role_split[1]


def break_role_id(role_id) -> broken_role_id:
    return broken_role_id(role_id=role_id)
