import time

import jwt
import pytest
from unittest import mock

from simple_github.auth import AppAuth, AppInstallationAuth, TokenAuth


@pytest.mark.asyncio
async def test_token_auth_get_token():
    token = "123"
    auth = TokenAuth(token)
    assert await auth.get_token() == token


@pytest.mark.asyncio
async def test_app_auth_get_token(privkey, pubkey):
    id = 42
    auth = AppAuth(id, privkey)
    token = await auth.get_token()

    payload = jwt.decode(token, pubkey, algorithms=["RS256"])
    assert payload["iss"] == id
    assert payload["exp"] == payload["iat"] + 540

    # Calling again yields the same token
    assert await auth.get_token() == token

    # Unless it will expire in under a minute
    with mock.patch.object(time, "time", return_value=payload["exp"] - 61):
        new_token = await auth.get_token()
        assert new_token == token

    with mock.patch.object(time, "time", return_value=payload["exp"] - 59):
        new_token = await auth.get_token()
        assert new_token != token


@pytest.mark.asyncio
async def test_app_installation_auth_get_token(aioresponses, privkey):
    app_id = 42
    inst_id = 100
    owner = "mozilla"
    auth = AppInstallationAuth(app=AppAuth(app_id, privkey), owner=owner)

    aioresponses.get(
        "/app/installations",
        status=200,
        payload=[{"id": inst_id, "account": {"login": owner}}],
    )
    aioresponses.post(
        f"/app/installations/{inst_id}/access_tokens",
        status=200,
        payload={"token": "111"},
    )
    token = await auth.get_token()
    assert token == "111"

    # Calling again yields the same token
    assert await auth.get_token() == token

    # Unless it will expire in under a minute
    aioresponses.post(
        f"/app/installations/{inst_id}/access_tokens",
        status=200,
        payload={"token": "222"},
    )
    cur = int(time.time())
    with mock.patch.object(time, "time", return_value=cur + 3600 - 61):
        new_token = await auth.get_token()
        assert new_token == token

    with mock.patch.object(time, "time", return_value=cur + 3600 - 59):
        new_token = await auth.get_token()
        assert new_token != token
