"""Regression tests for the Ebeco API client (custom_components/ebeco/data_handler.py).

They run against a fake ebecoconnect.com, so no account and no Home Assistant
are needed:  python -m pytest tests
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_fetch_user_device_returns_result(api, fake_ebeco):
    device = await api.fetch_user_device(1118)

    assert device == fake_ebeco.DEVICE
    method, path, auth, _ = fake_ebeco.requests[-1]
    assert (method, path) == ("GET", "/api/services/app/Devices/GetUserDeviceById/")
    assert auth == "Bearer tok"
    assert fake_ebeco.login_count == 1


async def test_fetch_user_devices_returns_list(api, fake_ebeco):
    assert await api.fetch_user_devices() == [fake_ebeco.DEVICE]


async def test_token_is_reused_between_requests(api, fake_ebeco):
    await api.fetch_user_device(1118)
    await api.fetch_user_device(1118)

    assert fake_ebeco.login_count == 1
    assert fake_ebeco.device_count == 2


async def test_http_error_raises_after_retries(api, fake_ebeco, data_handler, no_sleep):
    """Issue #48: used to return None, which crashed the climate entity."""
    fake_ebeco.device_responses = [(503, {"error": "down"})] * 10

    with pytest.raises(data_handler.EbecoApiError, match="HTTP 503"):
        await api.fetch_user_device(1118)

    assert fake_ebeco.device_count == 4  # 1 attempt + 3 retries
    assert fake_ebeco.login_count == 1  # a 5xx does not invalidate the token
    assert no_sleep == [1, 1, 1]


async def test_transient_http_error_recovers(api, fake_ebeco, no_sleep):
    fake_ebeco.device_responses = [(502, {}), (200, {"result": fake_ebeco.DEVICE})]

    assert await api.fetch_user_device(1118) == fake_ebeco.DEVICE
    assert fake_ebeco.device_count == 2


async def test_rate_limit_stops_immediately_and_keeps_token(
    api, fake_ebeco, data_handler, no_sleep
):
    """Ebeco allows 10 requests/10 s: on 429 we must not pile on retries."""
    fake_ebeco.device_responses = [(429, {}), (200, {"result": fake_ebeco.DEVICE})]

    with pytest.raises(data_handler.EbecoApiError, match="HTTP 429"):
        await api.fetch_user_device(1118)
    assert fake_ebeco.device_count == 1
    assert no_sleep == []

    # Next poll works without logging in again
    assert await api.fetch_user_device(1118) == fake_ebeco.DEVICE
    assert fake_ebeco.login_count == 1


async def test_expired_token_is_renewed(api, fake_ebeco, no_sleep):
    fake_ebeco.device_responses = [(401, {}), (200, {"result": fake_ebeco.DEVICE})]

    assert await api.fetch_user_device(1118) == fake_ebeco.DEVICE
    assert fake_ebeco.login_count == 2
    assert fake_ebeco.requests[-1][2] == "Bearer tok"


async def test_timeout_raises_timeout_error(api, fake_ebeco, no_sleep):
    """Issue #49/#53: a server that never answers ends in TimeoutError."""
    fake_ebeco.device_responses = [(200, "hang")] * 10

    with pytest.raises(TimeoutError):
        await api.fetch_user_device(1118)

    assert fake_ebeco.device_count == 4


async def test_timeout_then_success_recovers(api, fake_ebeco, no_sleep):
    fake_ebeco.device_responses = [(200, "hang"), (200, {"result": fake_ebeco.DEVICE})]

    assert await api.fetch_user_device(1118) == fake_ebeco.DEVICE
    assert fake_ebeco.login_count == 1  # a timeout does not invalidate the token


async def test_empty_result_raises(api, fake_ebeco, data_handler):
    fake_ebeco.device_responses = [(200, {"result": None})]

    with pytest.raises(data_handler.EbecoApiError, match="Empty response"):
        await api.fetch_user_device(1118)


async def test_login_http_error_raises_auth_error(api, fake_ebeco, data_handler):
    """Old issue #23: the login response was never checked."""
    fake_ebeco.login_responses = [(500, {"error": {"message": "Invalid"}})]

    with pytest.raises(data_handler.EbecoAuthError, match="HTTP 500"):
        await api.fetch_user_device(1118)

    assert fake_ebeco.device_count == 0


async def test_login_without_token_raises_auth_error(api, fake_ebeco, data_handler):
    fake_ebeco.login_responses = [(200, {"result": None})]

    with pytest.raises(data_handler.EbecoAuthError, match="did not contain a token"):
        await api.fetch_user_device(1118)


async def test_login_backs_off_on_rate_limit(api, fake_ebeco, no_sleep):
    fake_ebeco.login_responses = [(429, {}), (429, {})]

    assert await api.fetch_user_device(1118) == fake_ebeco.DEVICE
    assert fake_ebeco.login_count == 3
    assert no_sleep == [1, 2]


async def test_login_timeout_is_retried(api, fake_ebeco, monkeypatch, no_sleep):
    real_post = fake_ebeco.websession.post
    calls = []

    async def slow_first_post(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            await fake_ebeco.real_sleep(60)
        return await real_post(url, **kwargs)

    monkeypatch.setattr(fake_ebeco.websession, "post", slow_first_post)

    assert await api.fetch_user_device(1118) == fake_ebeco.DEVICE
    assert len(calls) == 2


async def test_set_powerstate_puts_json(api, fake_ebeco):
    await api.set_powerstate({"id": 1118, "powerOn": False})

    method, path, auth, body = fake_ebeco.requests[-1]
    assert (method, path) == ("PUT", "/api/services/app/Devices/UpdateUserDevice")
    assert auth == "Bearer tok"
    assert body == {"id": 1118, "powerOn": False}


async def test_set_temperature_and_preset_put_json(api, fake_ebeco):
    await api.set_room_target_temperature(
        {"id": 1118, "powerOn": True, "temperatureSet": 23}
    )
    await api.set_preset_mode({"id": 1118, "selectedProgram": "Home"})

    bodies = [r[3] for r in fake_ebeco.requests if r[0] == "PUT"]
    assert bodies == [
        {"id": 1118, "powerOn": True, "temperatureSet": 23},
        {"id": 1118, "selectedProgram": "Home"},
    ]
