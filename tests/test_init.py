"""Set-up, polling and failure handling of the Ebeco integration in a real
Home Assistant test core, with the cloud API mocked."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from .conftest import ALL_ENTITIES, DEVICE_URL, TOKEN_URL, entity_id, register_api


async def _poll(hass, freezer):
    """Advance past the 1-minute refresh interval and let the poll run."""
    freezer.tick(timedelta(minutes=1, seconds=1))
    async_fire_time_changed(hass)
    # The refresh runs as a background task, which plain block_till_done skips
    await hass.async_block_till_done(wait_background_tasks=True)


async def test_setup_creates_all_entities(hass, setup_integration):
    assert setup_integration.state is ConfigEntryState.LOADED

    for domain, unique_id in ALL_ENTITIES:
        state = hass.states.get(entity_id(hass, domain, unique_id))
        assert state is not None, (domain, unique_id)
        assert state.state != STATE_UNAVAILABLE, (domain, unique_id)

    assert hass.states.get(entity_id(hass, "climate", "1118")).state == "heat"


async def test_setup_logs_in_once_and_sends_bearer_token(
    hass, setup_integration, mock_api
):
    calls = [(m, str(u)) for m, u, *_ in mock_api.mock_calls]
    assert calls.count(("POST", TOKEN_URL)) == 1
    headers = [h for m, u, d, h in mock_api.mock_calls if str(u) == DEVICE_URL][0]
    assert headers["Authorization"] == "Bearer tok"


async def test_api_error_makes_entities_unavailable_then_recovers(
    hass, setup_integration, mock_api, device_data, freezer, caplog
):
    """Issue #48: a non-200 answer used to crash with None['powerOn']."""
    mock_api.clear_requests()
    mock_api.post(TOKEN_URL, json={"result": {"accessToken": "tok"}})
    mock_api.get(DEVICE_URL, status=503, json={"error": "down"})

    await _poll(hass, freezer)

    for domain, unique_id in ALL_ENTITIES:
        assert hass.states.get(entity_id(hass, domain, unique_id)).state == (
            STATE_UNAVAILABLE
        ), (domain, unique_id)
    assert "Error fetching Ebeco data: EbecoApiError: HTTP 503" in caplog.text
    # No crash: the only traceback is the coordinator's own DEBUG "Full error"
    assert "NoneType" not in caplog.text
    assert not [
        r for r in caplog.records if r.levelno >= logging.ERROR and r.exc_info
    ]

    register_api(mock_api, device_data)

    await _poll(hass, freezer)

    assert hass.states.get(entity_id(hass, "climate", "1118")).state == "heat"
    for domain, unique_id in ALL_ENTITIES:
        assert hass.states.get(entity_id(hass, domain, unique_id)).state != (
            STATE_UNAVAILABLE
        ), (domain, unique_id)


async def test_timeout_is_named_in_the_log(
    hass, setup_integration, mock_api, freezer, caplog
):
    """Issue #49/#53: the log line used to end with an empty message."""
    mock_api.clear_requests()
    mock_api.post(TOKEN_URL, json={"result": {"accessToken": "tok"}})
    mock_api.get(DEVICE_URL, exc=TimeoutError())

    await _poll(hass, freezer)

    assert hass.states.get(entity_id(hass, "climate", "1118")).state == (
        STATE_UNAVAILABLE
    )
    assert "Error fetching Ebeco data: TimeoutError" in caplog.text
    assert "Error fetching Ebeco data: \n" not in caplog.text


async def test_empty_result_makes_entities_unavailable(
    hass, setup_integration, mock_api, freezer, caplog
):
    mock_api.clear_requests()
    mock_api.post(TOKEN_URL, json={"result": {"accessToken": "tok"}})
    mock_api.get(DEVICE_URL, json={"result": None})

    await _poll(hass, freezer)

    assert hass.states.get(entity_id(hass, "climate", "1118")).state == (
        STATE_UNAVAILABLE
    )
    assert "Empty response from Ebeco API" in caplog.text


async def test_setup_retries_when_api_is_down(
    hass, config_entry, aioclient_mock, no_sleep_ha
):
    aioclient_mock.post(TOKEN_URL, status=503, json={})

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
    assert hass.states.get("climate.uterum") is None


async def test_unload_entry(hass, setup_integration):
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert setup_integration.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get(entity_id(hass, "climate", "1118")).state == (
        STATE_UNAVAILABLE
    )
